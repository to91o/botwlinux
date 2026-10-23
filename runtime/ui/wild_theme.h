// Original vector ornaments and a shared slate / parchment palette.
#pragma once
#include "imgui.h"

inline void wild_theme_style() {
    ImGuiStyle &s = ImGui::GetStyle();
    ImGui::StyleColorsDark();
    s.WindowRounding = 3; s.ChildRounding = 3; s.FrameRounding = 2;
    s.GrabRounding = 2; s.TabRounding = 0;
    s.WindowPadding = ImVec2(28, 24); s.FramePadding = ImVec2(14, 8);
    s.ItemSpacing = ImVec2(14, 12); s.WindowBorderSize = 1;
    s.ChildBorderSize = 1; s.ScrollbarSize = 14;
    ImVec4 *c = s.Colors;
    const ImVec4 blue(0.25f, 0.77f, 0.90f, 1), gold(0.86f, 0.76f, 0.53f, 1);
    c[ImGuiCol_Text] = ImVec4(0.94f, 0.91f, 0.82f, 1);
    c[ImGuiCol_TextDisabled] = ImVec4(0.56f, 0.64f, 0.63f, 1);
    c[ImGuiCol_WindowBg] = ImVec4(0.025f, 0.065f, 0.085f, 0.97f);
    c[ImGuiCol_ChildBg] = ImVec4(0.035f, 0.085f, 0.105f, 0.70f);
    c[ImGuiCol_PopupBg] = ImVec4(0.025f, 0.065f, 0.085f, 0.99f);
    c[ImGuiCol_Border] = ImVec4(0.60f, 0.56f, 0.40f, 0.65f);
    c[ImGuiCol_FrameBg] = c[ImGuiCol_Button] = ImVec4(0.08f, 0.17f, 0.20f, 1);
    c[ImGuiCol_FrameBgHovered] = c[ImGuiCol_ButtonHovered] = ImVec4(0.12f, 0.32f, 0.37f, 1);
    c[ImGuiCol_FrameBgActive] = c[ImGuiCol_ButtonActive] = ImVec4(0.13f, 0.42f, 0.49f, 1);
    c[ImGuiCol_Header] = c[ImGuiCol_Tab] = ImVec4(0.07f, 0.14f, 0.17f, 1);
    c[ImGuiCol_HeaderHovered] = c[ImGuiCol_TabHovered] = ImVec4(0.12f, 0.32f, 0.37f, 1);
    c[ImGuiCol_HeaderActive] = c[ImGuiCol_TabSelected] = ImVec4(0.11f, 0.27f, 0.32f, 1);
    c[ImGuiCol_TabSelectedOverline] = c[ImGuiCol_CheckMark] = blue;
    c[ImGuiCol_SliderGrab] = gold; c[ImGuiCol_SliderGrabActive] = blue;
    c[ImGuiCol_NavCursor] = blue;
    c[ImGuiCol_Separator] = ImVec4(0.60f, 0.56f, 0.40f, 0.50f);
    c[ImGuiCol_TitleBg] = c[ImGuiCol_TitleBgActive] = c[ImGuiCol_WindowBg];
}

inline void wild_panel_frame(float scale) {
    ImDrawList *dl = ImGui::GetWindowDrawList();
    const ImVec2 p = ImGui::GetWindowPos(), sz = ImGui::GetWindowSize();
    const float inset = 7 * scale, arm = 22 * scale;
    const ImU32 gold = IM_COL32(194, 175, 124, 190);
    for (int corner = 0; corner < 4; ++corner) {
        const float dx = corner & 1 ? -1.0f : 1.0f, dy = corner & 2 ? -1.0f : 1.0f;
        ImVec2 c(p.x + (dx > 0 ? inset : sz.x - inset), p.y + (dy > 0 ? inset : sz.y - inset));
        dl->AddLine(c, ImVec2(c.x + dx * arm, c.y), gold, scale);
        dl->AddLine(c, ImVec2(c.x, c.y + dy * arm), gold, scale);
        dl->AddCircleFilled(ImVec2(c.x + dx * 4 * scale, c.y + dy * 4 * scale), 1.5f * scale,
                            IM_COL32(83, 203, 229, 220));
    }
    // A quiet parchment rule under the heading, with a blue diamond seal.
    const float y = p.y + 74 * scale, x = p.x + sz.x * 0.5f, r = 4 * scale;
    dl->AddLine(ImVec2(p.x + 28 * scale, y), ImVec2(x - 12 * scale, y), gold);
    dl->AddLine(ImVec2(x + 12 * scale, y), ImVec2(p.x + sz.x - 28 * scale, y), gold);
    dl->AddQuadFilled(ImVec2(x, y - r), ImVec2(x + r, y), ImVec2(x, y + r), ImVec2(x - r, y),
                       IM_COL32(83, 203, 229, 220));
}
