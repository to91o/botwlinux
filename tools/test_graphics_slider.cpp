#include <cassert>
#include <cmath>
#include <cstdio>
#include <string>
#include "imgui.h"
#include "ui/option_rows.h"
const char *tr(const char *s) { return s; }
std::string tr_upper(const char *s) { return s; }
static float value=100; static ImVec2 a,b;
static void frame(bool disabled=false) {
 ImGui::NewFrame();ImGui::SetNextWindowPos(ImVec2(0,0));ImGui::SetNextWindowSize(ImVec2(1000,700));
 ImGui::Begin("Graphics",nullptr,ImGuiWindowFlags_NoSavedSettings);
 opt_begin("graphics",1);if(disabled)opt_disable_next();
 opt_slider("Render scale",&value,50,150,5,100,"%g%%","Resolution");
 a=ImGui::GetItemRectMin();b=ImGui::GetItemRectMax();opt_end();ImGui::End();ImGui::Render();
}
int main() {
 ImGui::CreateContext();auto &io=ImGui::GetIO();io.DisplaySize=ImVec2(1000,700);io.DeltaTime=1.f/60;
 io.IniFilename=nullptr;io.ConfigInputTrickleEventQueue=false;
 unsigned char *pixels;int w,h;io.Fonts->GetTexDataAsRGBA32(&pixels,&w,&h);
 frame();frame();float x0=a.x+16,x1=b.x-140,y=b.y-6;
 io.AddMousePosEvent(x0,y);frame();io.AddMouseButtonEvent(0,true);frame();assert(value==50);
 io.AddMousePosEvent(x0+.75f*(x1-x0),y);frame();assert(value==125);
 io.AddMouseButtonEvent(0,false);frame();assert(value==125);
 io.AddMousePosEvent(x1,y);frame(true);io.AddMouseButtonEvent(0,true);frame(true);assert(value==125);
 io.AddMouseButtonEvent(0,false);frame(true);assert(value==125);
 ImGui::DestroyContext();puts("Slider dragging, release, snapping and disabled-state checks passed.");
}
