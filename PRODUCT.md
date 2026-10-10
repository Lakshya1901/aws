# Product

<!-- impeccable:product-schema 1 -->

## Platform

android

React Native with Expo, one codebase. Android is the primary demo device; iOS runs the same screens through Expo Go (CLAUDE.md 14.1).

## Users

Primary: the FPO dispatch manager, who each morning decides who harvests, how much, and where each truck goes for a few hundred growers. Every word on screen is written at a farmer's reading level: users read short lines in their own language and know kg and Rs prices, but not technical terms. Rescue user: a city mandi trader with unsold stock at the end of the day. Secondary: individual farmers asking by voice; district horticulture officers watching the Glut Radar. (Confirmed October 10, 2026; CLAUDE.md Section 4.)

## Product Purpose

AnnaSetu tells the user where a load of produce should go today (sell fresh, hold, process, donate, feed, biogas or compost) and what it will earn after costs, so food is not sent into a market crash or dumped. Success: the user picks a better outlet for a load, understands why, and can repeat the reason.

## Positioning

One router with three entry points: Prevent (route a load before it leaves the farm, spreading loads so AnnaSetu never floods a market itself), Rescue (unsold stock at a city mandi to processors and food banks), Recover (inedible part to feed, biogas or compost). Built on public mandi prices and arrivals, turned into a per-load decision.

## Operating Context

Used on low-to-mid Android phones, outdoors and in sunlight, on slow connections. The user is mid-task (a truck is waiting), uses WhatsApp and phone calls, not dashboards. Headline city: Delhi (Azadpur mandi, Rescue and Recover); users type their city, town or village. Languages: English plus India's 20 most spoken languages (most machine-drafted, pending native review); voice input in the 12 that Amazon Transcribe supports; spoken replies in Hindi and English only.

## Capabilities and Constraints

- Screens: Language, Today (Glut Radar), New load (voice or form), Confirm, Recommendation, Today's plan, Unsold stock, Impact (CLAUDE.md 14.2).
- Risk words are Safe / Watch / Glut, always colour + word + icon (CLAUDE.md 14.5, 14.6).
- Recommendation card order: earnings first, then waste avoided, redirected (never merged with waste avoided), extra distance; buttons Why not {market}?, Listen, Use this (CLAUDE.md 14.3).
- Every figure carries a range or "(estimate)"; stale data is flagged; nothing is invented (CLAUDE.md 20).
- Mode is `same_day`: no "days early" wording anywhere.
- A recommendation is advice, not a confirmed sale or a partnered receiver.

## Evidence on Hand

Real replayed AGMARKNET prices and arrivals (demo days 2023-09-29 and 2025-03-19), NASA POWER weather, Amazon Location routes, seeded outlets from desk research ("Not yet partnered"). No user testing yet; Hindi and Kannada strings await native-speaker review.

## Product Principles

1. Answer first: where to send it, then why, then the cost of the choice.
2. Plain words a farmer uses; one idea per line.
3. Honest numbers: ranges and "estimate" stay visible, old data is never styled as current.
4. One main action per screen; everything else one tap away.
5. Voice helps at input and playback; text always remains.

## Accessibility & Inclusion

16 sp minimum body text, 24 sp key figures, 48 dp touch targets, high contrast readable in sunlight, status never by colour alone, regional scripts (Devanagari, Kannada) rendered and tested, layouts that survive longer Hindi and Kannada strings.
