#ifndef CLIPPER_CONTAINER_RPC_HPP
#define CLIPPER_CONTAINER_RPC_HPP

#include <thread>

#include <zmq.hpp>
#include <sstream>

#include <boost/circular_buffer.hpp>

#include "container_parsing.hpp"
#include <clipper/datatypes.hpp>
#include <clipper/logging.hpp>
#include <clipper/rpc_service.hpp>

const std::string LOGGING_TAG_CONTAINER = "CONTAINER";

using Clock = std::chrono::system_clock;

namespace clipper {

namespace container {

constexpr long SOCKET_POLLING_TIMEOUT_MILLIS = 5000;
constexpr long SOCKET_ACTIVITY_TIMEOUT_MILLIS = 30000;

template<class I>
class Model {
 public:
  Model(const std::string name, int version, InputType input_type) :
      name_(name), version_(version), input_type_(input_type) {

  }

  virtual std::vector<std::string> predict(const std::vector<std::shared_ptr<I>> inputs) = 0;

  std::string name_;
  int version_;
  InputType input_type_;

};

class RPC {
 public:
  RPC() : active_(false), event_history_(EVENT_HISTORY_CAPACITY) {

  }

  ~RPC() {
    stop();
  }

  // TODO(czumar): MOVE AND COPY CONSTRUCTORS

  template<typename D, class I>
  void start(Model<I> model, InputParser<D, I>& input_parser, const std::string &clipper_ip, int clipper_port) {
    if(active_) {
      throw std::runtime_error("Cannot start a container that is already started!");
    }
    active_ = true;
    const std::string clipper_address = "tcp://" + clipper_ip + ":" + std::to_string(clipper_port);
    serving_thread_ = std::thread([this, clipper_address, model, &input_parser](){
      serve_model(model, input_parser, clipper_address);
    });
  };

  void stop() {
    if(active_) {
      active_ = false;
      serving_thread_.join();
    }
  }

 private:
  std::thread serving_thread_;
  std::atomic_bool active_;
  boost::circular_buffer<rpc::RPCEvent> event_history_;
  static const size_t EVENT_HISTORY_CAPACITY = 100;


  template<typename D, class I>
  void serve_model(Model<I>& model, InputParser<D, I>& input_parser, const std::string& clipper_address) {
    zmq::context_t context(1);
    bool connected = false;
    std::chrono::time_point<Clock> last_activity_time;

    std::vector<long> input_header_buffer;
    std::vector<uint8_t> output_buffer;

    while(true) {
      zmq::socket_t socket = socket_t(context, ZMQ_DEALER);
      zmq::pollitem_t items[] = {{socket, 0, ZMQ_POLLIN, 0}};
      socket.connect(clipper_address);
      send_heartbeat(socket);

      while(active_) {
        zmq_poll(items, 1, SOCKET_POLLING_TIMEOUT_MILLIS);
        if (!(items[0].revents & ZMQ_POLLIN)) {
          if (connected) {
            std::chrono::time_point<Clock> curr_time = Clock::now();
            auto time_since_last_activity = curr_time.time_since_epoch() - last_activity_time.time_since_epoch();
            long time_since_last_activity_millis =
                std::chrono::duration_cast<std::chrono::milliseconds>(time_since_last_activity).count();
            if (time_since_last_activity_millis >= SOCKET_ACTIVITY_TIMEOUT_MILLIS) {
              log_info(LOGGING_TAG_CONTAINER, "Connection timed out, reconnecting...");
              socket.close();
              break;
            } else {
              send_heartbeat(socket);
            }
          } else {
            // We weren't connected previously, so let's keep polling
            continue;
          }
        }

        connected = true;
        last_activity_time = Clock::now();

        zmq::message_t msg_delimiter;
        zmq::message_t msg_msg_type_bytes;

        socket.recv(&msg_delimiter, 0);
        socket.recv(&msg_msg_type_bytes, 0);

        rpc::MessageType message_type =
            static_cast<rpc::MessageType>(static_cast<int *>(msg_msg_type_bytes.data())[0]);

        switch(message_type) {
          case rpc::MessageType::Heartbeat:
            log_info(LOGGING_TAG_CONTAINER, "Received heartbeat!");
            event_history_.push_back(rpc::RPCEvent::ReceivedHeartbeat);
            handle_heartbeat(model, socket);
            break;

          case rpc::MessageType::ContainerContent: {
            event_history_.push_back(rpc::RPCEvent::ReceivedContainerContent);
            zmq::message_t msg_request_id;
            zmq::message_t msg_request_header;

            socket.recv(&msg_request_id, 0);
            socket.recv(&msg_request_header, 0);

            int msg_id = static_cast<int *>(msg_request_id.data())[0];
            RequestType request_type =
                static_cast<RequestType>(static_cast<int *>(msg_request_header.data())[0]);

            switch(request_type) {
              case RequestType::PredictRequest:
                handle_predict_request(model, input_parser, socket, input_header_buffer, msg_id);
                break;

              case RequestType::FeedbackRequest:
                // Do nothing for now
                break;

              default:
                break;
            }

          } break;

          case rpc::MessageType::NewContainer:
            event_history_.push_back(rpc::RPCEvent::ReceivedContainerMetadata);
            log_error_formatted(LOGGING_TAG_CONTAINER, "Received erroneous new container message from Clipper!");
          default:
            break;
        }
      }

      // The container is no longer active. Close the socket
      // and exit the connection loop
      socket.close();
      return;
    }
  }

  template<typename D, class I>
  void handle_predict_request(
      Model<I>& model,
      InputParser<D, I>& input_parser,
      zmq::socket_t &socket,
      std::vector<long>& input_header_buffer,
      std::vector<uint8_t>& output_buffer,
      int msg_id) const {
    zmq::message_t msg_input_header_size;
    socket.recv(&msg_input_header_size, 0);
    long input_header_size_bytes = static_cast<long*>(msg_input_header_size.data())[0];

    // Resize input header buffer if necessary
    if(static_cast<long>((input_header_buffer.size() / sizeof(long))) < input_header_size_bytes) {
      input_header_buffer.resize(2 * (input_header_size_bytes) / sizeof(long));
    }
    // Receive input header
    socket.recv(input_header_buffer.data(), 0);
    InputType input_type = static_cast<InputType>(input_header_buffer[0]);
    if(input_type != model.input_type_) {
      std::stringstream ss;
      ss << "Received prediction request with incorrect input type: " << get_readable_input_type(input_type)
         << "for model with input type: " << get_readable_input_type(model.input_type_);
      throw std::runtime_error(ss.str());
    }

    zmq::message_t msg_raw_content_size;
    socket.recv(&msg_raw_content_size, 0);
    long input_content_size_bytes = static_cast<long*>(msg_raw_content_size.data())[0];

    std::vector<D> buffer = input_parser.get_data_buffer(input_content_size_bytes);
    // Receive input content
    socket.recv(buffer.data(), input_content_size_bytes, 0);

    std::vector<std::shared_ptr<I>> inputs =
        input_parser.get_inputs(input_header_buffer, input_content_size_bytes);

    // Make predictions
    std::vector<std::string> outputs = model.predict(inputs);

    // Send the outputs as a prediction response

    int num_outputs = static_cast<int>(outputs.size());

    // The output buffer begins with the number of outputs
    // encoded as an integer
    long response_size_bytes = sizeof(int);

    for(int i = 0; i < num_outputs; i++) {
      int output_length = static_cast<int>(outputs[i].length());
      // The output buffer contains the size of each output
      // encoded as an integer
      response_size_bytes += sizeof(int);
      response_size_bytes += output_length;
    }

    if(static_cast<long>(output_buffer.size()) < response_size_bytes) {
      output_buffer.resize(2 * response_size_bytes);
    }

    int* output_int_view = reinterpret_cast<int *>(output_buffer.data());
    output_int_view[0] = num_outputs;
    // Advance the integer output buffer to the correct position
    // for the output lengths content
    output_int_view++;

    uint8_t* output_byte_view = reinterpret_cast<uint8_t *>(output_buffer.data());
    // Advance the byte output buffer to the correct position for the
    // output content
    output_byte_view += sizeof(int) + (num_outputs * sizeof(int));

    for(int i = 0; i < num_outputs; i++) {
      int output_length = static_cast<int>(outputs[i].length());
      output_int_view[i] = output_length;
      memcpy(output_byte_view, outputs[i].data(), output_length);
      output_byte_view += output_length;
    }

    zmq::message_t msg_message_type(sizeof(int));
    static_cast<int*>(msg_message_type.data())[0] = static_cast<int>(rpc::MessageType::ContainerContent);

    zmq::message_t msg_message_id(sizeof(int));
    static_cast<int *>(msg_message_id.data())[0] = msg_id;

    zmq::message_t msg_prediction_response(output_buffer.data(), response_size_bytes, NULL);

    socket.send("", 0, ZMQ_SNDMORE);
    socket.send(&msg_message_type, ZMQ_SNDMORE);
    socket.send(&msg_message_id, ZMQ_SNDMORE);
    socket.send(&msg_prediction_response, 0);
    event_history_.push_back(rpc::RPCEvent::SentContainerContent);
  }

  template <class I>
  void handle_heartbeat(Model<I> &model, zmq::socket_t &socket) const {
    zmq::message_t msg_heartbeat_type;
    socket.recv(&msg_heartbeat_type, 0);
    rpc::HeartbeatType heartbeat_type
        = static_cast<rpc::HeartbeatType>(static_cast<int *>(msg_heartbeat_type.data())[0]);
    if(heartbeat_type == rpc::HeartbeatType::RequestContainerMetadata) {
      send_container_metadata(model, socket);
    }
  }

  void send_heartbeat(zmq::socket_t &socket) const {
    zmq::message_t type_message(sizeof(int));
    zmq::message_t heartbeat_type_message(sizeof(int));
    static_cast<int *>(type_message.data())[0] =
        static_cast<int>(rpc::MessageType::Heartbeat);
    static_cast<int *>(heartbeat_type_message.data())[0] = static_cast<int>(rpc::HeartbeatType::KeepAlive);
    socket.send("", 0, ZMQ_SNDMORE);
    socket.send(type_message, ZMQ_SNDMORE);
    socket.send(heartbeat_type_message);
    event_history_.push_back(rpc::RPCEvent::SentHeartbeat);
  }

  template <class I>
  void send_container_metadata(Model<I> &model, zmq::socket_t &socket) const {
    zmq::message_t msg_message_type(sizeof(int));
    static_cast<int*>(msg_message_type.data())[0] = static_cast<int>(rpc::MessageType::NewContainer);

    zmq::message_t msg_model_name(&model.name_[0], model.name_.length(), NULL);

    std::string model_version_str = std::to_string(model.version_);
    zmq::message_t msg_model_version(&model_version_str[0], model_version_str.length(), NULL);

    std::string model_input_type_str = std::to_string(model.input_type_);
    zmq::message_t msg_model_input_type(&model_input_type_str[0], model_input_type_str.length(), NULL);

    socket.send("", 0, ZMQ_SNDMORE);
    socket.send(&msg_message_type, ZMQ_SNDMORE);
    socket.send(&msg_model_name, ZMQ_SNDMORE);
    socket.send(&msg_model_version, ZMQ_SNDMORE);
    socket.send(&msg_model_input_type, 0);
    event_history_.push_back(rpc::RPCEvent::SentContainerMetadata);
  }
};

} // namespace container

} // namespace clipper
#endif //CLIPPER_CONTAINER_RPC_HPP
