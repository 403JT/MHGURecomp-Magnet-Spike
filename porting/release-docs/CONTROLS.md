# Magnet Spike controls — v0.1.0-alpha.5

Craft and equip an **MS** weapon from the Magnet Spike smithy category.
This guide describes the mod's inputs. The 160 converted action
entries include automatic transitions, recoveries and alternate lead-ins.

## Recovery at combo ends

The end of a combo now has added commitment before another attack, roll,
movement, guard, sheathe or mode switch can take over. Earlier attacks in the
combo retain their previous links. Inputs can still buffer for a valid follow-up;
buffering does not bypass the added recovery. Monster hit reactions interrupt
the hunter normally and clear the old recovery timer.

| Combo ending | Added recovery |
| --- | --- |
| Cutting vertical and horizontal final hits | 0.30 seconds |
| Impact Overhead Horizontal and Down Swipe | 0.40 seconds |
| Suplex and charged/weak Triple Strike releases | 0.50 seconds |
| Cutting / Impact aerial landing | 0.30 / 0.40 seconds |
| Both pin finishers | 0.50 seconds |

These are additions to the existing animation/cancel timing, measured in game
time. Charge holding and the earlier combo attacks do not receive this delay.

## Crafting and upgrading

Magnet Spike has its own weapon category on the smithy's third category page.
Most names have an **MS** prefix; the 13 corrected names instead end in **Magnet Spike** (see [NAME_CHANGES.md](NAME_CHANGES.md)). Its 136 weapon families copy the matching Great
Sword's materials, costs, unlocks and upgrade branches. Raw attack is 95% of the matching Great Sword,
with separate move damage tuning. Other equipment stats retain that baseline. Upgrade your
Magnet Spike through the normal equipment upgrade menu. A family retains its
model through its levels; branches to a different appearance change models.
The existing Great Sword tree remains available separately.

## Button legend

Combos below use **Switch labels** and buttons by position.
`+` means together; `→` means the next input during the follow-up window.

| Control | Position | Xbox |
| --- | --- | --- |
| X | Top face | Y |
| A | Right face | B |
| B | Bottom face | A |
| Y | Left face | X |
| R | Right shoulder | RB |
| ZR | Right trigger | RT |
| Minus | Minus / select | View / Back |

Hold a modifier such as R or ZR before pressing the face button. Release a
previous face-button press before a new X+A chord, then press X and A together.
Use MHGURecomp's keybinding settings to map these Switch buttons to your keyboard
and mouse. Right-stick aiming has been tested; mouse aim is not
covered by the same checks.

## Drawing, movement and switching

| Move | Input |
| --- | --- |
| Draw weapon while standing | X |
| Moving Cutting draw attack | Move + X while sheathed |
| Draw into Impact Guard | Hold R, press X+A while sheathed |
| Sheathe | Y while drawn, outside a combo |
| Ordinary roll | B, without aiming or holding R |
| Sprinting roll with weapon sheathed | Hold R + movement, then B |
| Switch Cutting / Impact | Minus from drawn neutral |
| Transform attack | Minus during a horizontal attack's follow-up window |
| Moving / post-roll attack variants | Move or roll, then X or A |
| Aerial attack | X during a jump: Cutting downslash or Impact falling swings |

Transform attacks continue the corresponding horizontal chain in the other
form. Sheathing resets the active form to Cutting. The port retains GU/Great
Sword adaptations for ordinary drawing, sheathing and locomotion.

## Cutting form

| Move | Input |
| --- | --- |
| Vertical Slash 1 | X from neutral |
| Upslash | X after Vertical 1; or X+A from neutral |
| Vertical Slash 2 | X after Upslash |
| Full vertical route | X → X → X |
| Horizontal Slash 1 | A from neutral |
| Horizontal Slash 2 | A after Horizontal 1 |
| Horizontal Slash 3 | A after Horizontal 2 |
| Full horizontal route | A → A → A |
| Finishing Slash | X+A after Vertical 2 or Horizontal 3 |
| Magnetic Double Slash | R+X |
| Magnetic Assault leap | R+X+A from neutral |
| Retreat Slash | R+B |
| Magnetic Evasion, two variants | R+Y or R+A |
| Evasion Upslash | X after either Magnetic Evasion |
| Timed Guard Counter | Hold R, press ZR just before an incoming hit |
| Counter follow-ups | X for Upslash, or X+A for Finishing Slash in its later window |

A successful guard automatically selects the counter appropriate to the
number of hits blocked. Magnetise adds the extra Finishing Slash hits
automatically.

## Impact form

| Move | Input |
| --- | --- |
| Down Swipe | X from neutral |
| Suplex | X+A from neutral |
| Triple Strike 1 | A while stationary |
| Triple Strike 2 | A after Triple Strike 1 |
| Triple Strike 3, uncharged | Start the third A input, then release before the charge cue |
| Charged Strike | A → A → hold A on the third input; release at the charge flash/sound |
| Horizontal Swipe 1 | A after Overhead Horizontal |
| Horizontal Swipe 2 | A after Horizontal 1 |
| Overhead Horizontal | X+A after Horizontal 2 |
| Suplex from that chain | X+A after Overhead Horizontal |
| Walking overhead variant | A while already walking with the weapon drawn |
| Magnetic Double Swipe | R+X |
| Magnetic Assault leap | R+X+A from neutral |
| Magnetic Evasion, two variants | R+Y or R+A |
| Additional magnetic evasion special | R+B |
| Magnetic Shock | X or A after an Impact magnetic evasion |
| Stronger Magnetic Shock | Evade through an enemy attack, then X or A |
| Timed guard | Hold R, press ZR just before an incoming hit |
| Guard Assault | After a successful guard, X or X+A selects its follow-up |

Holding the Triple Strike charge too long overcharges it and automatically
releases the weaker third strike. Use the charge cue rather than a fixed time
from the first attack. Stationary A and walking A start different Impact routes.
The previous guide's plain sheathed X+A draw was not reproduced with Guild
style in the latest checks. R+X+A while sheathed draws into Impact Guard;
the same chord while drawn remains Magnetic Assault.

B can roll out of the Triple Strike charge during its early and
late cancel windows. There is a short blocked interval between them. Moving
the stick uses the drawn-movement cancel where that window permits it.

## Marker, attraction and repulsion — either form

| Move | Input / requirement |
| --- | --- |
| Aim | Hold ZR without R; use the right stick |
| Magnetic Marker shot | ZR+A, aimed at a large monster |
| Attraction | With a marker more than 14 m and less than 40 m away, ZR+X |
| Repulsion | With a marker within 14 m, ZR+B |
| Cutting attraction follow-up | X during the approach for Falling Downslash |
| Impact attraction follow-up | X during the approach for Falling Swings; landing continues the sequence |
| Approach cancel | B during attraction |

Attraction and repulsion each need stamina and **one gauge bar**. Distance is
measured to the attached marker, so the target can move into or out of range.
Aiming keeps the normal third-person camera and uses the native pink Insect Glaive cursor. Attraction and repulsion still use the existing distance requirements.

## Magnetic Pin and finisher — either form

1. Start with at least **two gauge bars** and face a large monster.
2. Hold R and press X for Magnetic Double Slash / Double Swipe.
3. Release X, **keep R held**, then press X+A together during that attack's
   pin follow-up window.
4. Land the leap on the monster to start the restraint.
5. Tap X and A repeatedly during the hold to fill the gauge cells.
6. Filling the QTE automatically triggers that form's Pin Finisher. Waiting
   without enough successful presses ends the pin without the finisher.

R+X+A from neutral starts Magnetic Assault; its pin effect depends on taking
the follow-up from the double attack. The double attack and pin leap each
spend one bar. The current QTE uses gauge cells and an adapted GU monster hold.

## Magnetise — either form

Land attacks to charge each form independently. When the current form is ready,
press **R+Minus**. Its attacks receive the magnetised boost and supported extra
hits automatically for approximately **80 seconds**. A cooldown follows.

The five-bar movement gauge and each form's Magnetise charge are separate.
Most magnetic R attacks/evasions spend a gauge bar; switching form and a
marker shot do not spend one.

## Restored opening animations

The late Double Slash **X+A** follow-up now completes instead of stalling.
Three other attacks play restored lead-ins, delaying attack onset roughly
0.75–0.85 s relative to alpha.3. Existing input windows, damage values and end
recovery durations are unchanged. See [MOTION_FIXES.md](MOTION_FIXES.md).

## Validation scope

Fresh merged-build tests cover both forms' camera/cursor, pin shots and
attraction attacks, ordinary inputs into the previously stalled follow-up,
and all four restored motion timelines. The wider controls guide also reflects
historical tests; not every branch or all 160 entries was rerun on this build.
Connected multiplayer and a new full hunt remain untested. See
[COMPATIBILITY.md](COMPATIBILITY.md) and release-validation.json.
