#include <memory>
#include <random>
#include <chrono>
// uncomment to disable assert()
// #define NDEBUG
#include <cassert>
#include <sstream>

#include <clipper/metrics.hpp>
#include <clipper/task_executor.hpp>
#include <clipper/util.hpp>
#include <clipper/datatypes.hpp>

namespace clipper {

CacheEntry::CacheEntry() {}

PredictionCache::PredictionCache(size_t size_bytes)
    : max_size_bytes_(size_bytes) {
  lookups_counter_ = metrics::MetricsRegistry::get_metrics().create_counter(
      "internal:prediction_cache_lookups");
  hit_ratio_ = metrics::MetricsRegistry::get_metrics().create_ratio_counter(
      "internal:prediction_cache_hit_ratio");
}

folly::Future<Output> PredictionCache::fetch(
    const VersionedModelId &model, const std::shared_ptr<Input> &input) {
  std::unique_lock<std::mutex> l(m_);
  auto key = hash(model, input->hash());
  auto search = entries_.find(key);
  lookups_counter_->increment(1);
  if (search != entries_.end()) {
    // cache entry exists
    if (search->second.completed_) {
      // value already in cache
      hit_ratio_->increment(1, 1);
      search->second.used_ = true;
      // `makeFuture` takes an rvalue reference, so moving/forwarding
      // the cache value directly would destroy it. Therefore, we use
      // copy assignment to `value` and move the copied object instead
      Output value = search->second.value_;
      return folly::makeFuture<Output>(std::move(value));
    } else {
      // value not in cache yet
      folly::Promise<Output> new_promise;
      folly::Future<Output> new_future = new_promise.getFuture();
      search->second.value_promises_.push_back(std::move(new_promise));
      hit_ratio_->increment(0, 1);
      return new_future;
    }
  } else {
    // cache entry doesn't exist yet, so create entry
    CacheEntry new_entry;
    // create promise/future pair for this request
    folly::Promise<Output> new_promise;
    folly::Future<Output> new_future = new_promise.getFuture();
    new_entry.value_promises_.push_back(std::move(new_promise));
    insert_entry(key, new_entry);
    hit_ratio_->increment(0, 1);
    return new_future;
  }
}

void PredictionCache::put(const VersionedModelId &model,
                          const std::shared_ptr<Input> &input,
                          const Output &output) {
  std::unique_lock<std::mutex> l(m_);
  auto key = hash(model, input->hash());
  auto search = entries_.find(key);
  if (search != entries_.end()) {
    CacheEntry &entry = search->second;
    if (!entry.completed_) {
      // Complete the outstanding promises
      for (auto &p : entry.value_promises_) {
        p.setValue(std::move(output));
      }
      entry.completed_ = true;
      entry.value_ = output;
      size_bytes_ += output.y_hat_->size();
      evict_entries(size_bytes_ - max_size_bytes_);
    }
  } else {
    CacheEntry new_entry;
    new_entry.value_ = output;
    new_entry.completed_ = true;
    insert_entry(key, new_entry);
  }
}

void PredictionCache::insert_entry(const long key, CacheEntry &value) {
  size_t entry_size_bytes = value.completed_ ? value.value_.y_hat_->size() : 0;
  if (entry_size_bytes <= max_size_bytes_) {
    evict_entries(size_bytes_ + entry_size_bytes - max_size_bytes_);
    page_buffer_.insert(page_buffer_.begin() + page_buffer_index_, key);
    page_buffer_index_ = (page_buffer_index_ + 1) % page_buffer_.size();
    size_bytes_ += entry_size_bytes;
    entries_.insert(std::make_pair(key, std::move(value)));
  } else {
    // This entry is too large to cache
    log_error_formatted(LOGGING_TAG_TASK_EXECUTOR,
                        "Received an output of size: {} bytes that exceeds "
                        "cache size of: {} bytes",
                        entry_size_bytes, max_size_bytes_);
  }
}

void PredictionCache::evict_entries(long space_needed_bytes) {
  if (space_needed_bytes <= 0) {
    return;
  }
  while (space_needed_bytes > 0 && !page_buffer_.empty()) {
    long page_key = page_buffer_[page_buffer_index_];
    auto page_entry_search = entries_.find(page_key);
    if (page_entry_search == entries_.end()) {
      throw std::runtime_error(
          "Failed to find corresponding cache entry for a buffer page!");
    }
    CacheEntry &page_entry = page_entry_search->second;
    if (page_entry.used_ || !page_entry.completed_) {
      page_entry.used_ = false;
      page_buffer_index_ = (page_buffer_index_ + 1) % page_buffer_.size();
    } else {
      page_buffer_.erase(page_buffer_.begin() + page_buffer_index_);
      page_buffer_index_ = page_buffer_.size() > 0
                               ? page_buffer_index_ % page_buffer_.size()
                               : 0;
      size_bytes_ -= page_entry.value_.y_hat_->size();
      space_needed_bytes -= page_entry.value_.y_hat_->size();
      entries_.erase(page_entry_search);
    }
  }
}

size_t PredictionCache::hash(const VersionedModelId &model,
                             size_t input_hash) const {
  std::size_t seed = 0;
  size_t model_hash = std::hash<clipper::VersionedModelId>()(model);
  boost::hash_combine(seed, model_hash);
  boost::hash_combine(seed, input_hash);
  return seed;
}

///////////////////////////////////////////////////////

QueryCache2::QueryCache2(size_t size_bytes)
    : max_size_bytes_(size_bytes) {
  cache_seg_hist_ = metrics::MetricsRegistry::get_metrics().create_histogram(
      "cache seg latency", "microseconds", 1048576);
}

folly::Future<Output> QueryCache2::fetch(const VersionedModelId &model, const QueryId query_id) {
  auto before = std::chrono::system_clock::now();
  std::unique_lock<std::mutex> l(m_);
  auto key = hash(model, query_id);
  auto search = entries_.find(key);
  if (search != entries_.end()) {
    // cache entry exists
    if (search->second.completed_) {
      // value already in cache
      search->second.used_ = true;
      // `makeFuture` takes an rvalue reference, so moving/forwarding
      // the cache value directly would destroy it. Therefore, we use
      // copy assignment to `value` and move the copied object instead
      Output value = search->second.value_;
      return folly::makeFuture<Output>(std::move(value));
    } else {
      // value not in cache yet
      folly::Promise<Output> new_promise;
      folly::Future<Output> new_future = new_promise.getFuture();
      search->second.value_promises_.push_back(std::move(new_promise));
      return new_future;
    }
  } else {
    // cache entry doesn't exist yet, so create entry
    CacheEntry new_entry;
    // create promise/future pair for this request
    folly::Promise<Output> new_promise;
    folly::Future<Output> new_future = new_promise.getFuture();
    new_entry.value_promises_.push_back(std::move(new_promise));
    insert_entry(key, new_entry);
    auto after = std::chrono::system_clock::now();
    long seg_lat_micros = std::chrono::duration_cast<std::chrono::microseconds>(after - before).count();
    cache_seg_hist_->insert(seg_lat_micros);
    return new_future;
  }
}

void QueryCache2::put(const VersionedModelId &model, const QueryId query_id, Output output) {
  std::unique_lock<std::mutex> l(m_);
  auto key = hash(model, query_id);
  auto search = entries_.find(key);
  if (search != entries_.end()) {
    CacheEntry &entry = search->second;
    if (!entry.completed_) {
      // Complete the outstanding promises
      auto promises = std::move(search->second.value_promises_);
      entry.completed_ = true;
      entry.value_ = output;
      size_bytes_ += output.y_hat_->size();
      evict_entries(size_bytes_ - max_size_bytes_);
      l.unlock();
      for (auto &p : promises) {
        p.setValue(std::move(output));
      }
    }
  } else {
    CacheEntry new_entry;
    new_entry.value_ = output;
    new_entry.completed_ = true;
    insert_entry(key, new_entry);
  }
}

size_t QueryCache2::hash(const VersionedModelId &model,
                        const QueryId query_id) const {
  std::size_t seed = 0;
  size_t model_hash = std::hash<clipper::VersionedModelId>()(model);
  boost::hash_combine(seed, model_hash);
  boost::hash_combine(seed, query_id);
  return seed;
}

void QueryCache2::insert_entry(const long key, CacheEntry &value) {
  size_t entry_size_bytes = value.completed_ ? value.value_.y_hat_->size() : 0;
  if (entry_size_bytes <= max_size_bytes_) {
    evict_entries(size_bytes_ + entry_size_bytes - max_size_bytes_);
    page_buffer_.insert(page_buffer_.begin() + page_buffer_index_, key);
    page_buffer_index_ = (page_buffer_index_ + 1) % page_buffer_.size();
    size_bytes_ += entry_size_bytes;
    entries_.insert(std::make_pair(key, std::move(value)));
  } else {
    // This entry is too large to cache
    log_error_formatted(LOGGING_TAG_TASK_EXECUTOR,
                        "Received an output of size: {} bytes that exceeds "
                            "cache size of: {} bytes",
                        entry_size_bytes, max_size_bytes_);
  }
}

void QueryCache2::evict_entries(long space_needed_bytes) {
  if (space_needed_bytes <= 0) {
    return;
  }
  while (space_needed_bytes > 0 && !page_buffer_.empty()) {
    long page_key = page_buffer_[page_buffer_index_];
    auto page_entry_search = entries_.find(page_key);
    if (page_entry_search == entries_.end()) {
      throw std::runtime_error(
          "Failed to find corresponding cache entry for a buffer page!");
    }
    CacheEntry &page_entry = page_entry_search->second;
    if (page_entry.used_ || !page_entry.completed_) {
      page_entry.used_ = false;
      page_buffer_index_ = (page_buffer_index_ + 1) % page_buffer_.size();
    } else {
      page_buffer_.erase(page_buffer_.begin() + page_buffer_index_);
      page_buffer_index_ = page_buffer_.size() > 0
                           ? page_buffer_index_ % page_buffer_.size()
                           : 0;
      size_bytes_ -= page_entry.value_.y_hat_->size();
      space_needed_bytes -= page_entry.value_.y_hat_->size();
      entries_.erase(page_entry_search);
    }
  }
}


///////////////////////////////////////////////////////


QueryCache::QueryCache() {
  // lookups_counter_ = metrics::MetricsRegistry::get_metrics().create_counter(
  //     "internal:query_cache_lookups");
  // hit_ratio_ = metrics::MetricsRegistry::get_metrics().create_ratio_counter(
  //     "internal:query_cache_hit_ratio");
  cache_seg_hist_ = metrics::MetricsRegistry::get_metrics().create_histogram(
      "cache seg latency", "microseconds", 1048576);
}

folly::Future<Output> QueryCache::fetch(
    const VersionedModelId &model, const QueryId query_id) {
  std::unique_lock<std::mutex> l(m_);
  auto key = hash(model, query_id);
  auto search = cache_.find(key);
  // lookups_counter_->increment(1);
  if (search != cache_.end()) {
    // cache entry exists
    l.unlock();
    if (search->second.completed_) {
      // value already in cache
      // hit_ratio_->increment(1, 1);
      // `makeFuture` takes an rvalue reference, so moving/forwarding
      // the cache value directly would destroy it. Therefore, we use
      // copy assignment to `value` and move the copied object instead
      Output value = search->second.value_;
      return folly::makeFuture<Output>(std::move(value));
    } else {
      // value not in cache yet
      folly::Promise<Output> new_promise;
      folly::Future<Output> new_future = new_promise.getFuture();
      search->second.value_promises_.push_back(std::move(new_promise));
      // hit_ratio_->increment(0, 1);
      return new_future;
    }
  } else {
    // cache entry doesn't exist yet, so create entry
    CacheEntry new_entry;
    // create promise/future pair for this request
    folly::Promise<Output> new_promise;
    folly::Future<Output> new_future = new_promise.getFuture();
    new_entry.value_promises_.push_back(std::move(new_promise));
    auto before = std::chrono::system_clock::now();
    cache_.insert(std::make_pair(key, std::move(new_entry)));
    auto after = std::chrono::system_clock::now();
    long seg_lat_micros = std::chrono::duration_cast<std::chrono::microseconds>(after - before).count();
    cache_seg_hist_->insert(seg_lat_micros);
    return new_future;
  }
}

void QueryCache::put(const VersionedModelId &model,
                          const QueryId query_id,
                          Output output) {
  std::unique_lock<std::mutex> l(m_);
  auto key = hash(model, query_id);
  auto search = cache_.find(key);
  if (search != cache_.end()) {
    if (!search->second.completed_) {
      // Complete the outstanding promises
      search->second.completed_ = true;
      search->second.value_ = output;
      output.tid_ = std::hash<std::thread::id>()(std::this_thread::get_id());
      auto promises = std::move(search->second.value_promises_);
      l.unlock();
      // BEFORE
      for (auto &p : promises) {
        p.setValue(std::move(output));
      }
      // AFTER = WORST CASE 365 MICROS
    }
  } else {
    CacheEntry new_entry;
    new_entry.value_ = output;
    new_entry.completed_ = true;
    cache_.insert(std::make_pair(key, std::move(new_entry)));
  }
}

size_t QueryCache::hash(const VersionedModelId &model,
                             const QueryId query_id) const {
  std::size_t seed = 0;
  size_t model_hash = std::hash<clipper::VersionedModelId>()(model);
  boost::hash_combine(seed, model_hash);
  boost::hash_combine(seed, query_id);
  return seed;
}






}  // namespace clipper
