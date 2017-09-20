#ifndef CLIPPER_FRONTEND_RPC_SERVICE_HPP
#define CLIPPER_FRONTEND_RPC_SERVICE_HPP

#include <mutex>

#include <folly/ProducerConsumerQueue.h>
#include <wangle/concurrent/CPUThreadPoolExecutor.h>
#include <clipper/datatypes.hpp>
#include <zmq.hpp>

namespace zmq_frontend {

using namespace clipper;

const std::string LOGGING_TAG_ZMQ_FRONTEND = "ZMQ_FRONTEND";

// We may have up to 50,000 outstanding requests
constexpr size_t RESPONSE_QUEUE_SIZE = 50000;
constexpr size_t NUM_REQUESTS_RECV = 100;
constexpr size_t NUM_RESPONSES_SEND = 1000;

// Pair of input and request id
typedef std::pair<std::shared_ptr<Input>, int> FrontendRPCRequest;
// Pair of output and request id. Request id should match the id of a
// FrontendRPCRequest object
typedef std::pair<Output, int> FrontendRPCResponse;

class FrontendRPCService {
 public:
  FrontendRPCService();
  ~FrontendRPCService();

  FrontendRPCService(const FrontendRPCService &) = delete;
  FrontendRPCService &operator=(const FrontendRPCService &) = delete;

  void start(const std::string address, int send_port, int recv_port);
  void stop();
  void send_response(FrontendRPCResponse response);
  void add_application(std::string name,
                       std::function<void(FrontendRPCRequest)> app_function);

 private:
  void manage_send_service(const std::string ip, int port);
  void manage_recv_service(const std::string ip, int port);
  void handle_new_connection(zmq::socket_t &socket, int &client_id);
  void shutdown_service(zmq::socket_t &socket);
  void receive_request(zmq::socket_t &socket, size_t &request_id);
  void send_responses(zmq::socket_t &socket, size_t num_responses);

  std::mutex response_queue_insertion_mutex_;
  std::shared_ptr<folly::ProducerConsumerQueue<FrontendRPCResponse>>
      response_queue_;
  std::shared_ptr<wangle::CPUThreadPoolExecutor> prediction_executor_;
  std::atomic_bool active_;
  std::mutex app_functions_mutex_;
  std::mutex outstanding_requests_mutex_;
  std::mutex client_routing_mutex_;
  // Mapping from app name to prediction function
  std::unordered_map<std::string, std::function<void(FrontendRPCRequest)>>
      app_functions_;
  // Mapping from message id to client id
  std::unordered_map<size_t, size_t> outstanding_requests_;
  // Mapping from client id to routing id
  std::unordered_map<size_t, const std::vector<uint8_t>> client_routing_map_;
  std::thread rpc_send_thread_;
  std::thread rpc_recv_thread_;
};

}  // namespace zmq_frontend

#endif  // CLIPPER_FRONTEND_RPC_SERVICE_HPP