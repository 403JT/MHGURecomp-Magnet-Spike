# Insect Glaive-style Magnet Spike aiming

Included in the combined v0.1.0-alpha.5 release alongside the name and motion
fixes. Hold **ZR / right trigger**, without R, to keep the standard third-person
camera and display GU's native pink Glaive cursor at screen centre. Right-stick
aiming uses the normal camera settings, inversion and pitch limits.

**ZR+A / right face** fires the existing magnetic pin. With a valid marker more
than 14 m and less than 40 m away, stamina and one movement-gauge bar,
**ZR+X / top face** attracts the hunter. ZR+B repels when the marker is within
14 m. Distances are measured to the attached marker and change as the monster
moves. Release ZR to hide the cursor. Other bindings retain their existing
meaning. See [CONTROLS.md](CONTROLS.md).

The native Glaive reference uses neither the gunner aim byte nor quest-camera
aim mode. This port does the same. The Magnet Spike vtable's slot 342 supplies
the native Glaive cursor capability only for the local aiming hunter. It does
not call Glaive action handlers or access Glaive's larger private player fields.
The normal camera handles input once; the weapon reads its direction. Shot
speed, collision, marker attachment and distance requirements are unchanged.

The aim change is copied exactly from the alpha.3 Glaive-aim source: ms_act.c,
ms_class.c and ms.h. State layout is unchanged. The fresh combined-build tests
verify cursor/camera continuity, pin shots and completed attraction attacks in
both forms using Guild style. The standalone aim release's six-style tests
remain historical evidence; connected multiplayer and mouse aiming are not
covered by the fresh merged tests. See release-validation.json.
