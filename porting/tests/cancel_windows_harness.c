#include "../module/cancel_windows.c"
uint32_t g_main_base=0x200000;
static struct ms_state state;
static int raw_input=1;
struct ms_state *ms_find(uint8_t *p) { return p && state.p==p?&state:0; }
void logf(const char *fmt,...) {(void)fmt;}
unsigned fixture_setup(uint8_t *p,unsigned action,unsigned step,unsigned loops)
{
    state.p=p;state.action=(uint16_t)action;state.loops=(uint16_t)loops;
    FIELD(uint16_t,p,0x2506)=0x10;FIELD(uint16_t,p,0x250a)=(uint16_t)action;
    FIELD(uint8_t,p,5)=(uint8_t)step;
    for(unsigned i=0;i<sizeof window_tables/sizeof *window_tables;i++)
        if(window_tables[i].action==action && window_tables[i].step+1u==step) {
            FIELD(uint32_t,p,0x24ac)=window_tables[i].table;return window_tables[i].nrows;
        }
    FIELD(uint32_t,p,0x24ac)=9999;return 0;
}
unsigned fixture_time(uint8_t *p,unsigned rule,unsigned spec)
{
    return rule<sizeof window_rules/sizeof *window_rules && spec<4?
        (unsigned)time_passed(p,&state,&window_rules[rule].time[spec]):99;
}
void fixture_remove(void) {state.p=0;}
void fixture_clock(unsigned hundredths) {state.action_clock=(float)hundredths*0.01f;}
void fixture_input_mode(unsigned raw) {raw_input=(int)raw;}
int fixture_native_input(uint8_t *p,void *cmd)
{
    (void)p;(void)cmd;return raw_input;
}
int fixture_native_range(uint8_t *p,unsigned row)
{
    uint32_t regs[8]={0};regs[R0]=(uint32_t)(uintptr_t)p;regs[LR]=g_main_base+0x2ea984;
    return ms_local_cancel_range_c(regs,row)?(int)regs[R0]:0;
}
