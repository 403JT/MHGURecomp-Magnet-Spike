#include "moveset_harness.c"
void test_recovery_begin(uint8_t *p,unsigned no)
{
    __aeabi_memclr4(&s,sizeof s);s.p=p;s.action=(uint16_t)no;
    FIELD(uint16_t,p,0x2506)=0x10;FIELD(uint16_t,p,0x250a)=(uint16_t)no;
}
void test_recovery_clock(unsigned hundredths) {
#ifndef MS_TEST_OLD_RECOVERY
    s.action_clock=(float)hundredths*0.01f;
#else
    (void)hundredths;
#endif
}
void test_recovery_finish(uint8_t *p)
{
    const struct ms_action *a=find(s.action);finish(p,&s,a,a->nsteps-1);
}
#ifndef MS_TEST_OLD_RECOVERY
void test_recovery_tick(uint8_t *p,unsigned dt100,unsigned st,unsigned no)
{
    FIELD(float,p,0x1c)=(float)dt100*0.01f;
    FIELD(uint16_t,p,0x2506)=(uint16_t)st;FIELD(uint16_t,p,0x250a)=(uint16_t)no;
    recovery_clock(p,&s);
}
unsigned test_recovery_pending(void) {return s.recovery_end>0;}
#endif
