# Sheathed guard-draw correction — v0.1.0-alpha.3

With the weapon sheathed, hold R and press X+A together. This now draws into
the existing Impact Guard and finishes in Impact neutral. With the weapon
already drawn, R+X+A continues to perform Magnetic Assault.

The old sheathed chord selected the inherited Great Sword guard actions32/0
and32/2. The original Frontier standing/moving draw handlers1032d110/1032d210
select Magnet Spike112 (Impact Guard) for picked input9 (R1+triangle+circle).
The local x86 probe supplies the shared picker's result; the MHGU checks use
ordinary controller inputs. Both alternative attacks requested for comparison,
Impact draw79 and Magnetic Assault12, also execute when entered directly from
sheathed. They were diagnostic entries, not evidence of a normal input binding.

The correction replaces the inherited ground guard-draw route and applies
GU's existing draw-attack flag when Impact Guard starts sheathed. Aerial routes,
already drawn guards, attacks, gauge requirements, recovery and weapon stats
retain their previous behavior. No model, sound or other RomFS asset changed.

Validation includes70 compiled routing/initialization checks and ordinary
standing/moving guard draws on official Windows MHGURecomp0.18.0. The sprint-roll,
recovery, attack cancellation and state-ownership regressions were repeated.
All game tests were muted and used disposable save copies. Connected multiplayer
and a human reproduction of the video freeze remain outstanding.

The earlier guide's plain sheathed X+A Impact draw was not reproduced with
Guild style in these checks. It is no longer presented as a verified Guild binding.
