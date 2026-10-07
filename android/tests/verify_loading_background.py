"""Compile the real lookup/dialog methods with stubbed I/O and image decoder.
Run with Python 3 and a host C++20 compiler: python android/tests/verify_loading_background.py
Optional repository root argument permits checking the unpatched sources.
"""
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
def method(file, start, end):
    source = (root / file).read_text()
    return source[source.index(start):source.index(end, source.index(start))]
lookup = method('rpcs3/Emu/system_utils.cpp', '\tstd::string get_game_content_path(game_content_type type, const std::string& serial', '\n\tstd::pair<std::string, bool> get_game_content_path')
background = method('rpcs3/Emu/RSX/Overlays/overlay_message_dialog.cpp', '\t\tvoid message_dialog::update_custom_background()', '\n\t\tu32 message_dialog::progress_bar_count()')
preamble = r'''
#include <algorithm>
#include <cassert>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <memory>
#include <set>
#include <string>
#include <string_view>
#include <utility>
using u32 = uint32_t; using s32 = int32_t; using u16 = uint16_t; using u8 = uint8_t; using f32 = float;
enum class video_aspect { _16_9, _4_3 };
enum class game_content_type { content_icon, content_video, content_sound, overlay_picture, background_picture, background_picture_2 };
struct Number { u32 value = 0; u32 get() const { return value; } };
struct Config {
  struct { Number language; } sys;
  struct { video_aspect aspect_ratio = video_aspect::_16_9;
    struct { bool use_custom_background = true; Number blur_strength; Number darkening_strength; } shader_preloading_dialog;
  } video;
} g_cfg;
std::set<std::string> files, archive_files, decoded;
namespace fs {
 bool is_file(const std::string& path) { return files.contains(path); }
 std::string get_config_dir() { return "config"; }
}
struct iso_archive {
 iso_archive(const std::string&) {}
 bool is_valid() const { return true; }
 bool is_file(const std::string& path) const { return archive_files.contains(path); }
 bool exists(const std::string& path) const { return is_file(path); }
};
bool is_iso_file(const std::string& path) { return path.ends_with(".iso"); }
namespace fmt {
 std::string format(const char*, s32 lang) { return "_" + std::string(lang < 10 ? "0" : "") + std::to_string(lang); }
 std::string format(const char*, std::string_view name, const std::string& suffix, std::string_view extension) {
  return "/" + std::string(name) + suffix + "." + std::string(extension);
 }
}
[[maybe_unused]] struct { std::string GetTitleID() { return "GAME"; } std::string GetSfoDir(bool) { return "test directory"; } } Emu;
struct Logger {
 unsigned notices = 0, warnings = 0;
 template<class... Args> void notice(const char*, Args&&...) { ++notices; }
 template<class... Args> void warning(const char*, Args&&...) { ++warnings; }
} rsx_log;
std::string current_sfo, current_disc;
namespace rpcs3::utils {
'''
middle = r'''
std::string get_game_content_path(game_content_type type) {
 return get_game_content_path(type, "GAME", current_sfo, current_disc, {}, nullptr);
}
}
namespace rsx::overlays {
constexpr u16 virtual_width = 1280, virtual_height = 720;
struct color4f {
 float a = .85f;
 color4f() = default;
 color4f(float, float, float, float alpha) : a(alpha) {}
};
struct image_info {
 bool valid;
 int w = 1280, h = 720;
 image_info(const std::string& path) : valid(decoded.contains(path)) {}
 void* get_data() const { return valid ? reinterpret_cast<void*>(1) : nullptr; }
};
struct Poster {
 color4f fore_color, back_color;
 const image_info* image = nullptr;
 void set_size(u16, u16) {}
 void set_pos(u16, u16) {}
 void set_keep_aspect_ratio(bool) {}
 void set_raw_image(const image_info* i) { image = i; }
 void set_blur_strength(u8) {}
 void clear_image() { image = nullptr; }
};
struct message_dialog {
 bool custom_background_allowed = true;
 std::chrono::steady_clock::time_point next_background_search{};
 bool background_missing_logged = false;
 u32 background_blur_strength = 0, background_darkening_strength = 0;
 std::unique_ptr<image_info> background_image, background_overlay_image;
 Poster background, background_poster, background_overlay_poster;
 void update_custom_background();
};
'''
tests = r'''
}
int main() {
 using namespace rpcs3::utils;
 const auto path = [](game_content_type type, const std::string& sfo = "sfo", const std::string& disc = "disc") {
  return get_game_content_path(type, "GAME", sfo, disc, {}, nullptr);
 };
 // Mounted disc without artwork must not mask a valid installed image.
 files = {"sfo/PIC1.PNG"};
 assert(path(game_content_type::background_picture) == "sfo/PIC1.PNG");
 // Preserve disc precedence; localized content still wins over generic content.
 files.insert("disc/PIC1.PNG");
 assert(path(game_content_type::background_picture) == "disc/PIC1.PNG");
 files.insert("sfo/PIC1_00.PNG");
 assert(path(game_content_type::background_picture) == "sfo/PIC1_00.PNG");
 files.insert("disc/PIC1_00.PNG");
 assert(path(game_content_type::background_picture) == "disc/PIC1_00.PNG");
 files.insert("config/Icons/game_icons/GAME/PIC1.PNG");
 assert(path(game_content_type::background_picture) == "config/Icons/game_icons/GAME/PIC1.PNG");
 files = {"sfo/ICON0.PNG"};
 assert(path(game_content_type::content_icon, "sfo", "") == "sfo/ICON0.PNG");
 assert(path(game_content_type::content_icon, "sfo", "sfo") == "sfo/ICON0.PNG");
 assert(path(game_content_type::background_picture).empty());
 // Archive paths keep their archive flag, without requiring host filesystem files.
 files.clear(); archive_files = {"PS3_GAME/PIC1.PNG"}; bool in_archive = false;
 assert(get_game_content_path(game_content_type::background_picture, "GAME", "PS3_GAME", "", "game.iso", &in_archive) == "PS3_GAME/PIC1.PNG");
 assert(in_archive); archive_files.clear();
 // Decode failure must not retain a dead image and permanently stop fallbacks.
 current_sfo = "sfo"; current_disc = "disc";
 files = {"disc/PIC1.PNG", "disc/ICON0.PNG"}; decoded = {"disc/ICON0.PNG"};
 rsx::overlays::message_dialog dialog;
 dialog.update_custom_background();
 assert(dialog.background_image && dialog.background_image->get_data());
 assert(dialog.background_poster.image == dialog.background_image.get());
 assert(dialog.background.back_color.a == 0.f);
 // Alternative full background PIC3 is preferred over an icon.
 files.insert("disc/PIC3.PNG"); decoded.insert("disc/PIC3.PNG");
 rsx::overlays::message_dialog alternative;
 alternative.update_custom_background();
 assert(alternative.background_image && alternative.background_image->get_data());
 // Missing content can arrive after construction; the next permitted retry finds it.
 files.clear(); decoded.clear();
 rsx::overlays::message_dialog late;
 late.update_custom_background();
 assert(!late.background_image);
 const auto notices = rsx_log.notices;
 late.update_custom_background(); // No repeated log/filesystem search every frame.
 assert(rsx_log.notices == notices);
 files = {"sfo/PIC1.PNG"}; decoded = files;
 late.next_background_search = {}; // Advance the test's retry deadline without sleeping.
 late.update_custom_background();
 assert(late.background_image && late.background_image->get_data());
 // Disabling the feature releases raw-image references and restores the solid shade.
 g_cfg.video.shader_preloading_dialog.use_custom_background = false;
 late.update_custom_background();
 assert(!late.background_image && !late.background_poster.image);
 assert(late.background.back_color.a == .85f);
 std::cout << "PASS: disc/SFO fallback, locale/custom precedence, archive lookup, decode fallback, late mounts, disable\n";
}
'''
with tempfile.TemporaryDirectory() as temp:
    cpp = Path(temp) / 'background.cpp'
    exe = Path(temp) / 'background'
    cpp.write_text(preamble + lookup + middle + background + tests)
    subprocess.run(['c++', '-std=c++20', '-Wall', '-Wextra', '-Werror', str(cpp), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
