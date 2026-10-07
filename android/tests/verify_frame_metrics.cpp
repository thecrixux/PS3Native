#include "../app/src/main/cpp/frame_metrics.hpp"
#include <cassert>
#include <iostream>
#include <limits>
#include <thread>

using android_metrics::FrameMetrics;
int main() {
  FrameMetrics m;
  // Disabled consumers retain nothing, and each drained sample is consumed once.
  m.record(25);
  assert(m.drain_graph().empty());
  m.enable_graph(true);
  m.record(25);
  m.record(750); // A real hitch must not be filtered out.
  assert((m.drain_graph() == std::vector<float>{25, 750}));
  assert(m.drain_graph().empty());
  m.record(0);
  m.record(-2);
  m.record(std::numeric_limits<double>::quiet_NaN());
  m.record(std::numeric_limits<double>::infinity());
  assert(m.drain_graph().empty());
  m.enable_graph(false);

  // A known 40 FPS workload; the partial interval before Start is excluded.
  assert(m.start_capture());
  assert(!m.start_capture());
  m.record(999);
  for (int i = 0; i < 100; ++i) m.record(25);
  auto steady = m.stop_capture();
  assert(steady.frames.size() == 100 && steady.duration_ms == 2500);
  assert(steady.fps == 40 && steady.mean_ms == 25);
  assert(steady.p95_ms == 25 && steady.p99_ms == 25 && steady.max_ms == 25);
  assert(!steady.limit_reached);

  // Weighted FPS must fall with hitches; nearest-rank p99 must expose a long stall.
  assert(m.start_capture());
  m.record(1);
  for (int i = 0; i < 98; ++i) m.record(25);
  m.record(750);
  m.record(1000);
  auto hitches = m.stop_capture();
  assert(hitches.duration_ms == 4200 && hitches.fps > 23.8 && hitches.fps < 23.82);
  assert(hitches.p95_ms == 25 && hitches.p99_ms == 750 && hitches.max_ms == 1000);
  assert(hitches.frames[98] == 750 && hitches.frames[99] == 1000);

  // Recording is capped even if the UI has not stopped/exported yet.
  assert(m.start_capture());
  m.record(1);
  for (std::size_t i = 0; i < FrameMetrics::capture_limit + 10; ++i) m.record(25);
  auto capped = m.stop_capture();
  assert(capped.limit_reached && capped.frames.size() == FrameMetrics::capture_limit);
  assert(capped.fps == 40);
  assert(m.stop_capture().frames.empty());

  // The live graph has bounded storage and retains recent samples after a UI stall.
  m.enable_graph(true);
  for (std::size_t i = 1; i <= FrameMetrics::graph_limit + 10; ++i) m.record(i);
  auto graph = m.drain_graph();
  assert(graph.size() == FrameMetrics::graph_limit && graph.front() == 11);
  assert(graph.back() == FrameMetrics::graph_limit + 10);

  // A producer and graph consumer can run concurrently without duplicating samples.
  assert(m.start_capture());
  m.record(1);
  m.drain_graph();
  std::atomic<bool> finished{false};
  std::thread producer([&] {
    for (int i = 1; i <= 10000; ++i) m.record(i);
    finished.store(true);
  });
  float previous = 0;
  do {
    for (auto ms : m.drain_graph()) {
      assert(ms > previous);
      previous = ms;
    }
    std::this_thread::yield();
  } while (!finished.load());
  producer.join();
  for (auto ms : m.drain_graph()) { assert(ms > previous); previous = ms; }
  auto concurrent = m.stop_capture();
  assert(concurrent.frames.size() == 10000);
  for (int i = 0; i < 10000; ++i) assert(concurrent.frames[i] == i + 1);
  std::cout << "PASS: frame consumption, hitches, statistics, capture/graph limits, concurrent access\n";
}
