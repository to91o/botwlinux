#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <unistd.h>
static void child(const char *exe, const char *mode) {
 pid_t pid=fork(); assert(pid>=0);
 if(!pid) { execl(exe,exe,mode,(char *)0); _exit(127); }
 int status; assert(waitpid(pid,&status,0)==pid); assert(WIFEXITED(status) && WEXITSTATUS(status)==0);
}
#include "settings.h"
#include "nvn/output_scale.h"
bool bind_settings_load(const char *a, const char *b) { return false; }
void bind_settings_save(FILE *f) {}
int main(int argc,char **argv) {
 if(argc>1) {
  settings_load();
  if(argv[1][0]=='b') assert(g_settings.render_scale==1.5f && g_settings.fsr_sharpness==0);
  else assert(g_settings.render_scale==1 && fabsf(g_settings.fsr_sharpness-.87f)<.001);
  return 0;
 }
 g_settings.fullscreen=true;g_settings.fps_limit=30;g_settings.window_w=1280;g_settings.window_h=720;
 for(int i=GRAPHICS_LOW;i<GRAPHICS_CUSTOM;i++) {
  settings_apply_graphics_preset(i);assert(settings_graphics_preset()==i);
  assert(g_settings.fullscreen && g_settings.fps_limit==30 && g_settings.window_w==1280);
 }
 settings_apply_graphics_preset(GRAPHICS_BALANCED);
 OutScale a,b;output_scale(1280,720,false,&a);
 g_settings.render_scale=.5f;output_scale(1280,720,false,&b);
 assert(fabs(a.sx-b.sx)<1e-8 && fabs(a.scene_sx*.5-b.scene_sx)<1e-8);
 assert(settings_graphics_preset()==GRAPHICS_CUSTOM);
 g_settings.render_scale=.75f;g_settings.fsr_sharpness=.4f;settings_save();
 g_settings.render_scale=1;g_settings.fsr_sharpness=1;settings_load();
 assert(fabsf(g_settings.render_scale-.75f)<.001 && fabsf(g_settings.fsr_sharpness-.4f)<.001);
 FILE *f=fopen(getenv("SAVAGEWIND_SETTINGS"),"w");assert(f);
 fputs("settings_version = 3\nrender_scale = 900\nfsr_sharpness = -50\n",f);fclose(f);child(argv[0],"bounds");
 f=fopen(getenv("SAVAGEWIND_SETTINGS"),"w");assert(f);
 fputs("settings_version = 3\nrender_scale = nan\nfsr_sharpness = inf\n",f);fclose(f);child(argv[0],"nan");
 f=fopen(getenv("SAVAGEWIND_SETTINGS"),"w");assert(f);
 fputs("settings_version = 3\nrender_scale =\nfsr_sharpness =\n",f);fclose(f);
 child(argv[0],"empty");
 puts("Graphics preset, scale, persistence and input bounds checks passed.");
}
