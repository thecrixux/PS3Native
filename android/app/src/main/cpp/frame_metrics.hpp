#pragma once

#include <algorithm>
#include <atomic>
#include <cmath>
#include <deque>
#include <mutex>
#include <vector>

// RSX flip intervals, not GPU execution time or generated/displayed frames.
// No allocation or lock in the renderer while both consumers are disabled.
namespace android_metrics {
struct Capture {
  std::vector<float> frames;
  bool limit_reached = false;
  double duration_ms = 0;
  double mean_ms = 0;
  double fps = 0;
  float p95_ms = 0;
  float p99_ms = 0;
  float max_ms = 0;

  void summarize() {
    duration_ms = 0;
    mean_ms = fps = 0;
    p95_ms = p99_ms = max_ms = 0;
    if (frames.empty()) return;
    for (float ms : frames) duration_ms += ms;
    mean_ms = duration_ms / frames.size();
    fps = 1000.0 / mean_ms;
    auto sorted = frames;
    std::sort(sorted.begin(), sorted.end());
    const auto percentile = [&](double p) {
      return sorted[static_cast<std::size_t>(std::ceil(p * sorted.size())) - 1];
    };
    p95_ms = percentile(0.95);
    p99_ms = percentile(0.99);
    max_ms = sorted.back();
  }
};

class FrameMetrics {
public:
  static constexpr std::size_t capture_limit = 60000;
  static constexpr std::size_t graph_limit = 512;

  void enable_graph(bool enabled) {
    std::lock_guard lock(mutex);
    graph_enabled.store(enabled);
    graph.clear();
  }

  std::vector<float> drain_graph() {
    std::lock_guard lock(mutex);
    std::vector<float> result(graph.begin(), graph.end());
    graph.clear();
    return result;
  }

  bool start_capture() {
    std::lock_guard lock(mutex);
    if (recording.load()) return false;
    frames.clear();
    frames.reserve(capture_limit);
    limit_reached = false;
    skip_capture_interval = true; // The interval crossing the Start press is incomplete.
    recording.store(true);
    return true;
  }

  Capture stop_capture() {
    Capture result;
    {
      std::lock_guard lock(mutex);
      recording.store(false);
      result.frames.swap(frames);
      result.limit_reached = limit_reached;
      limit_reached = false;
    }
    result.summarize(); // Sort a copy after releasing the renderer's mutex.
    return result;
  }

  void record(double ms) {
    if (!std::isfinite(ms) || ms <= 0) return;
    if (!graph_enabled.load() && !recording.load()) return;
    std::lock_guard lock(mutex);
    if (graph_enabled.load()) {
      if (graph.size() == graph_limit) graph.pop_front();
      graph.push_back(static_cast<float>(ms));
    }
    if (recording.load()) {
      if (skip_capture_interval) {
        skip_capture_interval = false;
      } else {
        frames.push_back(static_cast<float>(ms));
        if (frames.size() == capture_limit) {
          limit_reached = true;
          recording.store(false);
        }
      }
    }
  }

private:
  std::atomic<bool> graph_enabled{false};
  std::atomic<bool> recording{false};
  std::mutex mutex;
  std::deque<float> graph;
  std::vector<float> frames;
  bool skip_capture_interval = false;
  bool limit_reached = false;
};
} // namespace android_metrics
