/* Independent Magnet Spike equipment type. GPL-3.0-or-later.
 * GU 1.4: type 7 is GS, unused type 12/class 5 is Magnet Spike.
 * Numeric IDs stay identical WITHIN separate namespaces. Native read-only GS
 * create/process rows are deliberately shared, preserving recipes. With
 * MS_BALANCE, private level copies change only raw and element fields.
 * Base records and their identity/name/model accessors are also cloned.
 */
#include "ms.h"
#include "smithy_tree.inc"
#ifdef MS_BALANCE
#include "ms_balance_data.inc"
static uint32_t level_rows[MS_TREE_LEVEL_COUNT][5];
#endif
#define GS_TYPE 7u
#define BASE_SLOTS 90
#define MODEL_FILE_FIRST 0x10b00u
typedef uint8_t *(*getter_t)(void *,uint32_t,uint32_t);
static uint32_t base_vt[2+BASE_SLOTS];
static uint32_t base_rows[MS_TREE_BASE_COUNT][10];
static uint8_t *original_rows[MS_TREE_BASE_COUNT];
static const char *name_sources[MS_TREE_BASE_COUNT][3];
static char names[MS_TREE_BASE_COUNT][3][64];
static unsigned initialized;
static uint32_t box_type(void) { return MS_TYPE; }

/* English display names requested for these MS families and upgrade variants.
 * Native GS records/text and all nonmatching MS names remain unchanged. */
static const struct {
    unsigned id;
    const char *original, *replacement;
} name_overrides[] = {
    {19, "Avidya Great Sword", "Avidya Magnet Spike"},
    {38, "Tigrex Great Sword", "Tigrex Magnet Spike"},
    {69, "Skeletal Great Sword", "Skeletal Magnet Spike"},
    {69, "Infernal Great Sword", "Infernal Magnet Spike"},
    {73, "Alatreon Great Sword", "Alatreon Magnet Spike"},
    {75, "Rusted Great Sword", "Rusted Magnet Spike"},
    {78, "Worn Great Sword", "Worn Magnet Spike"},
    {78, "Aged Great Sword", "Aged Magnet Spike"},
    {111, "Gold Great Sword", "Gold Magnet Spike"},
    {112, "Silverwing Great Sword", "Silverwing Magnet Spike"},
    {115, "Elderfrost Great Sword", "Elderfrost Magnet Spike"},
    {130, "Research Great Sword", "Research Magnet Spike"},
    {130, "Discovery Great Sword", "Discovery Magnet Spike"},
};
static const char *renamed_name(unsigned id,const char *source)
{
    for (unsigned i=0;i<sizeof name_overrides/sizeof name_overrides[0];i++) {
        if (name_overrides[i].id!=id) continue;
        const char *a=source,*b=name_overrides[i].original;
        while (*a && *a==*b) {a++;b++;}
        if (!*a && !*b) return name_overrides[i].replacement;
    }
    return 0;
}

static const char *tree_name(uint8_t *r,unsigned lv,int by_level)
{
    unsigned id=FIELD(uint32_t,r,4);
    if (id>=MS_TREE_BASE_COUNT || !original_rows[id]) return "Magnet Spike";
    uint8_t *gs=original_rows[id];
    typedef const char *(*name_t)(void *,unsigned);
    name_t get=(name_t)(*(uint32_t **)gs)[(by_level?0xbc:0x3c)/4];
    const char *source=get(gs,lv);
    if (!source) return "Magnet Spike";
    const char *replacement=renamed_name(id,source);
    if (replacement) return replacement;
    unsigned k;
    for (k=0;k<3;k++) if (name_sources[id][k]==source) return names[id][k];
    for (k=0;k<3 && name_sources[id][k];k++);
    if (k==3) k=2;
    char *out=names[id][k];out[0]='M';out[1]='S';out[2]=' ';
    unsigned n=0;
    while (source[n] && n<60) {out[n+3]=source[n];n++;}
    // Preserve UTF-8 when truncating a long localized name.
    if (source[n]) while (n && ((unsigned char)source[n]&0xc0)==0x80) n--;
    out[n+3]=0;name_sources[id][k]=source;
    return out;
}
static const char *w_name(uint8_t *r) { return tree_name(r,1,0); }
static const char *w_name_lv(uint8_t *r,unsigned lv) { return tree_name(r,lv,1); }
static const char *w_desc(void) { return "A Frontier Magnet Spike.\r\nGreat Sword crafting with\r\nMHGU-tuned damage."; }

int ms_base_c(uint32_t *regs)
{
    if (regs[R1]!=MS_TYPE) return 0;
    unsigned id=regs[R2];
    if (id>=MS_TREE_BASE_COUNT) {regs[R0]=0;return 1;}
    uint8_t *gs=FN(getter_t,0x13c208)((void *)regs[R0],GS_TYPE,id);
    if (!gs) {regs[R0]=0;return 1;}
    if (!initialized) {
        const uint32_t *vt=*(const uint32_t **)gs;
        for (int i=0;i<2+BASE_SLOTS;i++) base_vt[i]=vt[i-2];
        base_vt[2+0x18/4]=(uint32_t)box_type;
        base_vt[2+0x3c/4]=(uint32_t)w_name;
        base_vt[2+0x40/4]=(uint32_t)w_desc;
        base_vt[2+0xbc/4]=(uint32_t)w_name_lv;
        base_vt[2+0xc0/4]=(uint32_t)w_desc;
        initialized=1;
        logf("ms-tree: independent type 12; %u weapons, %u levels, %u models",
             MS_TREE_BASE_COUNT-1,MS_TREE_LEVEL_COUNT,MS_TREE_MODEL_COUNT);
    }
    uint8_t *r=(uint8_t *)base_rows[id];
    for (unsigned i=0;i<40;i++) r[i]=gs[i];
    *(uint32_t **)r=base_vt+2;
    FIELD(uint16_t,r,8)=ms_tree_models[id];
    // Sound routing is class scoped, with shared Frontier banks, not GS banks.
    FIELD(uint16_t,r,10)=1;
    original_rows[id]=gs;
    regs[R0]=(uint32_t)r;
    return 1;
}
int ms_base_find_c(uint32_t *regs) { return ms_base_c(regs); }
int ms_level_c(uint32_t *regs)
{
    if (regs[R1]!=MS_TYPE) return 0;
#ifdef MS_BALANCE
    unsigned index=regs[R2];
    if (index>=MS_TREE_LEVEL_COUNT) {regs[R0]=0;return 1;}
    uint8_t *gs=FN(getter_t,0x13ed08)((void *)regs[R0],GS_TYPE,index);
    if (!gs) {regs[R0]=0;return 1;}
    uint8_t *r=(uint8_t *)level_rows[index];
    for (unsigned i=0;i<20;i++) r[i]=gs[i];
    unsigned raw=FIELD(uint16_t,r,12),element=FIELD(uint16_t,r,16);
    raw=(raw*MS_BALANCE_RAW_PERCENT+50)/100;
    element=(element*MS_BALANCE_ELEMENT_PERCENT+50)/100;
    FIELD(uint16_t,r,12)=(uint16_t)raw;
    FIELD(uint16_t,r,16)=(uint16_t)element;
    regs[R0]=(uint32_t)r;return 1;
#else
    regs[R1]=GS_TYPE;return 0; // Original bounded native getter and vtables.
#endif
}
int ms_forge_create_c(uint32_t *regs)
{
    if (regs[R1]!=MS_TYPE) return 0;
    regs[R1]=GS_TYPE;return 0;
}
int ms_forge_process_c(uint32_t *regs)
{
    if (regs[R1]!=MS_TYPE) return 0;
    regs[R1]=GS_TYPE;return 0;
}
/* Native forge achievement counters compact out unused type 12 and otherwise
 * credit its forges to LBG. Suppress that unrelated saved counter. GU has no
 * independent saved Magnet Spike guild-card counter yet. */
int ms_tree_forge_count_c(uint32_t *regs) { return regs[R1]==MS_TYPE; }
int ms_weapon_element(uint32_t id,uint32_t *type,uint32_t *value)
{
    // Native element/level getters provide the exact equipped-level value.
    // The prototype's level-1-only fallback must not overwrite an upgrade.
    (void)id;(void)type;(void)value;return 0;
}

/* 0x286ac0 (hunter,class,part,model) -> file ID. Native class-5 IDs
 * only cover seven old MH3 models; never extend into another class's range. */
int ms_tree_model_file_c(uint32_t *regs)
{
    if (regs[R1]!=MS_CLASS) return 0;
    unsigned n=regs[R3];
    regs[R0]=regs[R2]==0 && n && n<=MS_TREE_MODEL_COUNT ? MODEL_FILE_FIRST+n-1:0;
    return 1;
}
int ms_tree_file_id(uint32_t *regs)
{
    unsigned n=regs[R1]-MODEL_FILE_FIRST;
    if (n>=MS_TREE_MODEL_COUNT) return 0;
    void *mgr=*(void **)MAIN(0x2126a64);
    if (!mgr) {regs[R0]=0;return 1;}
    typedef void *(*find_t)(void *,uint32_t,uint32_t,uint32_t);
    find_t find=(*(find_t **)mgr)[0x38/4];
    regs[R0]=(uint32_t)find(mgr,(uint32_t)find,ms_tree_model_hashes[n],0x58a15856);
    logf("ms-tree: model %u resource %x",n+1,regs[R0]);
    return 1;
}
