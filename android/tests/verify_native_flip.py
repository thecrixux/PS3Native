"""Exercise the real GraphicsFrame::flip with a deterministic clock and fake Emu.
Only the clock read is substituted; actual timing/reset/capture logic is compiled.
"""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / 'android/app/src/main/cpp/native-lib.cpp').read_text()
a = source.index('  void flip(draw_context_t ctx, bool skip_frame = false) override {')
b = source.index('  int client_width()', a)
flip = source[a:b].replace(' override', '').replace('std::chrono::steady_clock::now()', 'fake_now')
preamble = r'''
#include <atomic>
#include <cassert>
#include <chrono>
#include <iostream>
#include "frame_metrics.hpp"
using u32 = unsigned; using u64 = unsigned long long; using draw_context_t = void*;
android_metrics::FrameMetrics g_frame_metrics;
std::atomic<float> g_hud_fps{0}, g_hud_frametime{0}, g_hud_last_frame_ms{0};
auto fake_now = std::chrono::steady_clock::time_point(std::chrono::seconds(10));
struct {
 bool running = true; u64 pause_time = 0;
 bool IsRunning() const { return running; }
 u64 GetPauseTime() const { return pause_time; }
} Emu;
struct GraphicsFrame {
 std::chrono::steady_clock::time_point fpsWindowStart{}, lastFlip{};
 u32 fpsFrames = 0; u64 pauseTime = 0;
'''
tests = r'''
};
int main() {
 GraphicsFrame frame;
 const auto advance = [&](int ms, bool skipped = false) {
  fake_now += std::chrono::milliseconds(ms);
  frame.flip(nullptr, skipped);
 };
 frame.flip(nullptr);
 g_frame_metrics.enable_graph(true);
 assert(g_frame_metrics.start_capture());
 advance(25); // Partial Start interval is dropped from the capture.
 advance(25);
 advance(250, true); // Skipped flip is not a presented frame.
 advance(25); // Interval from the preceding actual flip is 275 ms.
 Emu.running = false;
 advance(5000); // Loading/paused overlay cannot enter a gameplay capture.
 assert(g_hud_fps.load() == 0 && g_hud_last_frame_ms.load() == 0);
 Emu.pause_time += 5000000;
 Emu.running = true;
 advance(0); // New baseline after pause.
 advance(25);
 // Pause/resume without any overlay flips must also discard the pause gap.
 Emu.running = false;
 fake_now += std::chrono::seconds(10);
 Emu.pause_time += 10000000;
 Emu.running = true;
 advance(0);
 advance(25);
 advance(750); // Real hitch during gameplay is preserved.
 assert(g_hud_last_frame_ms.load() == 750);
 auto result = g_frame_metrics.stop_capture();
 assert((result.frames == std::vector<float>{25, 275, 25, 25, 750}));
 assert(result.duration_ms == 1100 && result.max_ms == 750);
 assert((g_frame_metrics.drain_graph() == std::vector<float>{25, 25, 275, 25, 25, 750}));
 assert(g_frame_metrics.drain_graph().empty());
 std::cout << "PASS: actual flip integration, skipped frames, loading, pause/resume, long hitches\n";
}
'''
with tempfile.TemporaryDirectory() as temp:
    cpp, exe = Path(temp)/'flip.cpp', Path(temp)/'flip'
    cpp.write_text(preamble + flip + tests)
    subprocess.run(['c++', '-std=c++20', '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter', '-pthread', '-I', str(root/'android/app/src/main/cpp'), str(cpp), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
