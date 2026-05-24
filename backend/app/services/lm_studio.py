import httpx
import logging
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime
from backend.app.core.config import settings

logger = logging.getLogger("spotigem.lm_studio")

MODE_LABELS = {0: "minor", 1: "major"}

PROFILES_PATH = Path(settings.DATA_RAW_DIR).parent / "model_profiles.json"

GENRE_STRUCTURE_TEMPLATES = {
    "hip-hop": {
        "structure": "4-bar intro, 16-bar verse 1, 4-bar hook/chorus, 16-bar verse 2, 4-bar hook/chorus, 16-bar verse 3, 4-bar hook/chorus, 4-bar outro",
        "sections": "[Intro] → [Verse 1] (16 bars) → [Hook] (4 bars, catchy repeated phrase) → [Verse 2] (16 bars) → [Hook] → [Verse 3] (16 bars) → [Hook] → [Outro]",
        "instrumentation": "808 sub-bass, trap hi-hats (rapid 16th/32nd patterns), snare on 2 and 4, synth pads/brass stabs, vocal ad-libs, deep kick",
        "vocal_style": "Rhythmic flow with internal rhyme schemes, punchy delivery, ad-libs between bars. Hook is melodic and repetitive — the most memorable part.",
        "lyrics_style": "Verse-heavy storytelling or bragging, dense wordplay and rhyme schemes (AABB or AABB/ABAB mixed), conversational register, slang and cultural references. Hook is 2-4 lines repeated, simple and catchy. NO ballad-style pre-chorus or bridge.",
        "bpm_range": (75, 160),
        "typical_time_sig": "4/4",
        "avoid": "NO pre-chorus, NO pop bridge, NO acoustic strumming, NO I-V-vi-IV, NO boy band harmonies, NO autotune ballad, NO generic love lyrics",
    },
    "r&b": {
        "structure": "4-bar intro, 8-bar verse 1, 4-bar pre-chorus, 8-bar chorus, 8-bar verse 2, 4-bar pre-chorus, 8-bar chorus, 8-bar bridge (vocal run/gradation), 8-bar chorus, 4-bar outro",
        "sections": "[Intro] → [Verse 1] (8 bars) → [Pre-Chorus] (4 bars, building) → [Chorus] (8 bars, melodic and lush) → [Verse 2] (8 bars) → [Pre-Chorus] → [Chorus] → [Bridge] (8 bars, vocal showcase/run) → [Chorus] → [Outro]",
        "instrumentation": "Deep bass groove, smooth electric piano/Rhodes, muted guitar strums, programmed drums with swing, lush synth pads, occasional strings",
        "vocal_style": "Smooth, soulful delivery with melismatic runs. Chest voice mixed with falsetto. Call-and-response backing vocals. Emotionally expressive.",
        "lyrics_style": "Romantic or emotional themes, sensual imagery, poetic metaphors. Verses are narrative, pre-chorus builds tension, chorus is soaring and memorable. Bridge features vocal runs and key change feel. Use conversational but polished language.",
        "bpm_range": (60, 120),
        "typical_time_sig": "4/4",
        "avoid": "NO rock distortion, NO aggressive rap, NO folk strumming, NO I-V-vi-IV, NO boy band group vocals",
    },
    "pop": {
        "structure": "4-bar intro, 8-bar verse 1, 4-bar pre-chorus, 8-bar chorus, 8-bar verse 2, 4-bar pre-chorus, 8-bar chorus, 4-bar bridge, 8-bar chorus, 4-bar outro",
        "sections": "[Intro] → [Verse 1] (8 bars) → [Pre-Chorus] (4 bars, energy build) → [Chorus] (8 bars, hook-heavy) → [Verse 2] (8 bars) → [Pre-Chorus] → [Chorus] → [Bridge] (4 bars, breakdown/shift) → [Chorus] → [Outro]",
        "instrumentation": "Synth leads, programmed drums, bass guitar or synth bass, polished production, layered harmonies, electronic textures, bright pads",
        "vocal_style": "Clean, polished vocals with harmonized choruses. Front-and-center vocal production. Some ad-libs and vocal runs in the bridge.",
        "lyrics_style": "Universal relatable themes (love, freedom, nights out). Simple but evocative language. Strong rhyme schemes (AABB/ABAB). Chorus is the centerpiece — the most catchy part. Pre-chorus builds anticipation. Bridge provides contrast before final chorus lift.",
        "bpm_range": (95, 135),
        "typical_time_sig": "4/4",
        "avoid": "NO excessive autotune, NO generic party lyrics, NO I-V-vi-IV without variation, NO 2000s boy band production, NO predictable key change",
    },
    "rock": {
        "structure": "8-bar intro (riff-based), 16-bar verse 1, 8-bar chorus, 8-bar verse 2, 8-bar chorus, 8-bar guitar solo/bridge, 8-bar chorus, 4-bar outro",
        "sections": "[Intro] (8 bars, guitar riff + drums) → [Verse 1] (16 bars, quieter dynamic) → [Chorus] (8 bars, loud and anthemic) → [Verse 2] (16 bars) → [Chorus] → [Guitar Solo / Bridge] (8 bars, instrumental) → [Chorus] → [Outro] (riff + fade/crash)",
        "instrumentation": "Distorted electric guitars (rhythm + lead), bass guitar, drum kit (kick, snare, hi-hat, cymbals), optional acoustic guitar layer. Power chords on chorus. Guitar solo in bridge section.",
        "vocal_style": "Passionate, direct delivery. Verse vocals may be restrained, chorus vocals open up with power. Some grit/belting. Group vocals on chorus hooks.",
        "lyrics_style": "Rebellious, introspective, or narrative themes. Verse lyrics are descriptive and story-driven. Chorus is anthemic — short, powerful, sing-along lines. Bridge/solo section replaces traditional pop bridge. NO pre-chorus unless punk/surf subgenre. Straight verse-chorus-verse-chorus-solo-chorus.",
        "bpm_range": (100, 180),
        "typical_time_sig": "4/4",
        "avoid": "NO autotune, NO boy band harmonies, NO pre-chorus, NO synth pads, NO programmed pop drums, NO gentle falsetto, NO I-V-vi-IV",
    },
    "country": {
        "structure": "4-bar intro (pick/fiddle), 12-bar verse 1, 8-bar chorus, 12-bar verse 2, 8-bar chorus, 8-bar bridge (key change optional), 8-bar chorus, 4-bar outro",
        "sections": "[Intro] (4 bars, fingerpick or fiddle) → [Verse 1] (12 bars) → [Chorus] (8 bars, memorable and singable) → [Verse 2] (12 bars) → [Chorus] → [Bridge] (8 bars, storytelling shift or key change) → [Chorus] → [Outro]",
        "instrumentation": "Acoustic guitar (fingerpick or strum), steel/pedal steel guitar, fiddle, bass, drum kit (simple kit), optional piano or harmonica",
        "vocal_style": "Warm, twangy vocal delivery. Storytelling cadence. Close harmonies on chorus. Conversational but emotional.",
        "lyrics_style": "Narrative storytelling with vivid imagery (trucks, dirt roads, whiskey, small towns, heartbreak). Verse tells the story, chorus delivers the emotional core. Simple AAB or AABB rhyme schemes. Bridge shifts perspective or adds new story detail. NO urban slang, NO abstract metaphors — keep it concrete and vivid.",
        "bpm_range": (85, 140),
        "typical_time_sig": "4/4",
        "avoid": "NO electronic beats, NO autotune, NO hip-hop flow, NO abstract metaphors, NO urban slang, NO boy band harmonies, NO synth pads",
    },
    "metal": {
        "structure": "8-bar intro (heavy riff), 16-bar verse 1, 8-bar chorus, 8-bar verse 2, 8-bar chorus, 8-16 bar bridge/solo (guitar solo, breakdown or tempo change), 8-bar chorus, 4-bar outro",
        "sections": "[Intro] (8 bars, heavy distorted riff + double kick) → [Verse 1] (16 bars, aggressive) → [Chorus] (8 bars, powerful and memorable) → [Verse 2] (16 bars) → [Chorus] → [Bridge / Guitar Solo / Breakdown] (8-16 bars) → [Chorus] → [Outro] (heavy riff + crash)",
        "instrumentation": "Heavily distorted electric guitars (drop tuning common), bass (often distorted), double-kick drumming, blast beats in extreme subgenres, palm-muted riffs, guitar solo in bridge",
        "vocal_style": "Harsh vocals (growls, screams) or powerful clean vocals depending on subgenre. Aggressive delivery. Chorus may switch to melodic clean vocals. No gentle falsetto.",
        "lyrics_style": "Dark, aggressive, or epic themes (death, war, mythology, inner struggle, societal collapse). Visceral imagery, not romantic or gentle. Dense and intense verse lyrics. Chorus is powerful and chant-like. Bridge/solo section is INSTRUMENTAL. NO love ballad language.",
        "bpm_range": (100, 220),
        "typical_time_sig": "4/4",
        "avoid": "NO autotune, NO pop melody, NO acoustic guitar, NO romantic ballad, NO boy band harmonies, NO gentle falsetto, NO major key unless intentional",
    },
    "folk": {
        "structure": "4-bar intro (fingerpick), 16-bar verse 1, 8-bar chorus, 16-bar verse 2, 8-bar chorus, 8-bar bridge (instrumental or lighter verse), 8-bar chorus, 4-bar outro",
        "sections": "[Intro] (4 bars, gentle fingerpick) → [Verse 1] (16 bars, storytelling) → [Chorus] (8 bars, reflective and melodic) → [Verse 2] (16 bars, continues story) → [Chorus] → [Bridge] (8 bars, instrumental break or perspective shift) → [Chorus] → [Outro]",
        "instrumentation": "Acoustic guitar (fingerpicked), upright bass, light percussion (cajon, tambourine), optional fiddle, banjo, or mandolin. Sparse and warm production.",
        "vocal_style": "Intimate, warm, close-mic vocal. Gentle delivery, slight breathiness. Harmony vocals on chorus. Feels like the singer is in the room.",
        "lyrics_style": "Poetic storytelling with nature imagery, personal reflection, social commentary. Rich metaphors and vivid scenes. Verses are long and narrative, chorus is reflective. Simple ABAB or ABCB rhyme. NO electronic or urban references — keep it organic and timeless.",
        "bpm_range": (60, 140),
        "typical_time_sig": "4/4",
        "avoid": "NO electronic beats, NO autotune, NO heavy distortion, NO urban/club references, NO polished pop production, NO I-V-vi-IV, NO boy band vocals",
    },
    "jazz": {
        "structure": "8-bar intro, 16-bar head (melody/theme AABA or ABAC), 16-32 bar improvisation section, 16-bar head (reprise), 4-bar outro",
        "sections": "[Intro] (8 bars, piano/bass/drums setup) → [Head A] (8 bars, main theme) → [Head A'] (8 bars, theme variation) → [Head B] (8 bars, bridge/contrasting theme) → [Head A] (8 bars, return) → [Solo Section] (16-32 bars, instrumental improv over chord changes) → [Head] (reprise of theme) → [Outro] (tag or fade)",
        "instrumentation": "Piano (voiced chords, comping), upright bass (walking lines), drum kit (brushes or sticks, swing feel), optional saxophone or trumpet (lead melody + solo), vibraphone",
        "vocal_style": "If vocal: smooth, warm, slightly behind the beat. Scat singing or melodic interpretation. Never belting or aggressive. Conversational phrasing with space.",
        "lyrics_style": "Sophisticated, poetic language with nuance and ambiguity. Themes of urban life, romance, nostalgia, introspection. AABA form common. Verses have internal rhyme and swing rhythm. Minimal and evocative — leave space for the music. NO pop hooks or repetitive choruses.",
        "bpm_range": (60, 200),
        "typical_time_sig": "4/4",
        "avoid": "NO pop hooks, NO repetitive 4-chord loops, NO autotune, NO drum machine, NO generic love lyrics, NO verse-chorus-bridge pop structure",
    },
    "indie": {
        "structure": "8-bar intro (atmospheric/reverb), 12-bar verse 1, 8-bar chorus, 12-bar verse 2, 8-bar chorus, 8-bar bridge (textural shift/dynamics), 8-bar chorus, 4-bar outro (fade or noise)",
        "sections": "[Intro] (8 bars, reverb guitar + synth pad) → [Verse 1] (12 bars, intimate) → [Chorus] (8 bars, bigger dynamics but still restrained) → [Verse 2] (12 bars) → [Chorus] → [Bridge] (8 bars, textural change — noise, quiet breakdown, or key shift) → [Chorus] → [Outro] (fade or noise swell)",
        "instrumentation": "Jangly or reverb-washed electric guitars, synth pads/textures, bass, drum kit (often roomy/natural sound), optional glockenspiel, organ, or found sounds",
        "vocal_style": "Intimate, slightly detached delivery. Verse vocals are close and quiet, chorus opens up but remains raw. Lo-fi aesthetic. Slight imperfections are part of the charm.",
        "lyrics_style": "Abstract, literary, or stream-of-consciousness themes. Unusual metaphors, specific and quirky imagery. Verses are more important than chorus — storytelling and mood over hooks. Chorus is more atmospheric than catchy. Bridge shifts texture rather than key. NO generic love lyrics — be specific and idiosyncratic.",
        "bpm_range": (80, 150),
        "typical_time_sig": "4/4",
        "avoid": "NO polished pop production, NO autotune, NO generic love lyrics, NO I-V-vi-IV, NO boy band harmonies, NO club beats",
    },
    "electronic": {
        "structure": "16-bar intro/build, 16-bar drop 1, 8-bar breakdown, 16-bar drop 2, 8-bar outro",
        "sections": "[Intro / Build-Up] (16 bars, adding layers — kick, then bass, then synth, then riser) → [Drop 1] (16 bars, full energy — main synth/bass hook, 4-on-floor kick) → [Breakdown] (8 bars, strip back to pads/vocals, tension builds) → [Drop 2] (16 bars, variation of drop 1 + new element) → [Outro] (8 bars, fade or filter out)",
        "instrumentation": "Synth leads (saw, supersaw), sub-bass (sine or 808), 4-on-floor kick drum, hi-hats, claps, risers/filters, arpeggiators, pad chords, sidechain compression on bass/pads",
        "vocal_style": "If vocal: short chopped phrases, repetitive hooks, processed/reverb vocals. NOT a full lyrical song — vocals serve the groove. Vocal chops and samples as texture.",
        "lyrics_style": "Minimal lyrics — short phrases, repetitive hooks, vocal chops. Lyrics serve the groove and energy, not storytelling. Drop sections are often instrumental. Breakdown may have a brief vocal line. Use sparse, evocative phrases: NOT full verses and choruses. Think 8-16 lines total, not 40.",
        "bpm_range": (115, 175),
        "typical_time_sig": "4/4",
        "avoid": "NO full verse-chorus-verse, NO traditional pop lyrics, NO acoustic guitar, NO ballad dynamics, NO long storytelling verses, NO I-V-vi-IV",
    },
    "reggae": {
        "structure": "4-bar intro (rhythm guitar skank), 12-bar verse 1, 8-bar chorus, 12-bar verse 2, 8-bar chorus, 8-bar bridge (dub/bass drop section), 8-bar chorus, 4-bar outro",
        "sections": "[Intro] (4 bars, skank guitar + one-drop rhythm) → [Verse 1] (12 bars) → [Chorus] (8 bars, singalong) → [Verse 2] (12 bars) → [Chorus] → [Bridge / Dub Section] (8 bars, bass-heavy, stripped back) → [Chorus] → [Outro]",
        "instrumentation": "Offbeat rhythm guitar (skank/chuck), deep bass (melodic walking lines), one-drop drumming (kick on 1, rimshot on 3), organ shuffle/bubble, optional horn section or backing vocal trio",
        "vocal_style": "Laid-back, warm delivery. Slightly behind the beat. Call-and-response with backing vocal trio. Chorus is singalong with harmonies.",
        "lyrics_style": "Social justice, spirituality, love, or everyday resilience themes. Simple but powerful language. Verses tell the story, chorus is the rallying cry. Bridge/dub section strips back to bass and drums. Positive or righteous tone — even sad songs have hope.",
        "bpm_range": (65, 110),
        "typical_time_sig": "4/4",
        "avoid": "NO 4-on-floor kick (use one-drop), NO pop progression, NO autotune, NO aggressive delivery, NO electronic builds/drops, NO boy band harmonies",
    },
    "soul": {
        "structure": "4-bar intro (horns/guitar), 12-bar verse 1, 4-bar pre-chorus, 8-bar chorus, 12-bar verse 2, 4-bar pre-chorus, 8-bar chorus, 8-bar bridge (vocal showcase/horn break), 8-bar chorus (with vamp/fade), 4-bar outro",
        "sections": "[Intro] (4 bars, horns + guitar lick) → [Verse 1] (12 bars) → [Pre-Chorus] (4 bars, building) → [Chorus] (8 bars, powerful and soaring) → [Verse 2] (12 bars) → [Pre-Chorus] → [Chorus] → [Bridge] (8 bars, vocal showcase or horn break) → [Chorus] (with vamp/fade) → [Outro]",
        "instrumentation": "Horn section (trumpet, sax, trombone), Hammond organ, electric guitar (clean/funk), bass (melodic and groovy), drum kit (tight pocket), backing vocal trio",
        "vocal_style": "Powerful, passionate delivery with gospel influence. Belting on chorus, smooth on verses. Call-and-response with backing singers. Vocal runs and melisma on bridge.",
        "lyrics_style": "Emotional depth, themes of love, struggle, resilience, and joy. Verses are personal and direct. Pre-chorus builds intensity. Chorus is the emotional peak — soaring and repeatable. Bridge is a vocal showcase. Language is warm and authentic, not polished or abstract.",
        "bpm_range": (65, 120),
        "typical_time_sig": "4/4",
        "avoid": "NO electronic beats, NO autotune, NO rock distortion, NO folk acoustic simplicity, NO I-V-vi-IV, NO boy band production, NO thin programmed drums",
    },
    "blues": {
        "structure": "4-bar intro, 12-bar verse 1 (AAB form), 12-bar verse 2, 12-bar verse 3, 8-bar solo/guitar break, 12-bar verse 4, 4-bar turnaround/outro",
        "sections": "[Intro] (4 bars, guitar lick) → [Verse 1] (12 bars, AAB: statement-repeat-response) → [Verse 2] (12 bars, AAB) → [Verse 3] (12 bars, AAB) → [Solo / Guitar Break] (8-12 bars, instrumental) → [Verse 4] (12 bars, AAB) → [Turnaround / Outro]",
        "instrumentation": "Electric or acoustic guitar (bending strings, vibrato), bass, drum kit (shuffle or straight feel), optional harmonica, piano. Guitar solos between verses.",
        "vocal_style": "Raw, emotive delivery. Bending notes, gritty tone. Call-and-response between vocal and guitar (vocal line → guitar answers). Feels like live performance.",
        "lyrics_style": "AAB form: first line states theme, second line repeats (with variation), third line resolves or answers. Themes of hardship, loss, travel, and resilience. Concrete imagery — trains, crossroads, whiskey, rain. Simple but emotionally powerful. NO abstract metaphors, NO pop structures (no pre-chorus, no bridge, no key changes).",
        "bpm_range": (60, 140),
        "typical_time_sig": "4/4",
        "avoid": "NO pop verse-chorus, NO pre-chorus, NO bridge, NO key change, NO autotune, NO electronic production, NO abstract lyrics, NO boy band",
    },
    "latin": {
        "structure": "8-bar intro (percussion + brass), 16-bar verse 1, 8-bar chorus (catchy, singalong), 16-bar verse 2, 8-bar chorus, 8-bar bridge (percussion break or guiro/montuno), 8-bar chorus, 4-bar outro (fade with percussion)",
        "sections": "[Intro] (8 bars, percussion + brass riff) → [Verse 1] (16 bars) → [Chorus] (8 bars, catchy and danceable) → [Verse 2] (16 bars) → [Chorus] → [Bridge / Percussion Break / Montuno] (8 bars) → [Chorus] → [Outro] (fade with percussion)",
        "instrumentation": "Congas, timbales, bongos, clave, güiro, bass (tumbao pattern), piano (montuno), brass section (trumpets, trombone), guitar (rasgueado or fingerpick depending on subgenre)",
        "vocal_style": "Passionate, rhythmic delivery. Call-and-response (sonero improvisation in salsa). Chorus is high-energy and singalong. Bridge features percussion breakdown or piano montuno. Ad-libs and exclamations (¡azúcar!, ¡eh!, ¡dale!)",
        "lyrics_style": "Themes of love, dance, celebration, nostalgia, or longing. Rhythmic and percussive language — lyrics must groove with the beat. Verses tell stories or set scenes, chorus is the hook everyone sings. Bridge/percussion break is often instrumental. Mix of poetic and street language depending on subgenre.",
        "bpm_range": (80, 180),
        "typical_time_sig": "4/4",
        "avoid": "NO programmed pop drums (use real percussion), NO boy band harmonies, NO I-V-vi-IV, NO English-only lyrics, NO generic fiesta cliches, NO thin synthesized production",
    },
}

GENRE_ALIASES_FOR_TEMPLATES = {
    "rap": "hip-hop", "trap": "hip-hop", "hiphop": "hip-hop",
    "rnb": "r&b", "rhythm and blues": "r&b",
    "edm": "electronic", "dance": "electronic", "techno": "electronic",
    "house": "electronic", "trance": "electronic", "drum and bass": "electronic",
    "punk": "rock", "pop-punk": "rock", "alt-rock": "rock",
    "grunge": "rock", "emo": "rock", "hard-rock": "rock",
    "cuarteto": "latin", "reggaeton": "latin", "cumbia": "latin",
    "bachata": "latin", "salsa": "latin", "samba": "latin",
    "sertanejo": "latin", "mpb": "latin", "bossa nova": "latin",
    "singer-songwriter": "folk",
    "funk": "soul",
    "heavy metal": "metal", "death metal": "metal", "thrash": "metal",
    "indie rock": "indie",
}


def _resolve_genre_template(genre: Optional[str]) -> Optional[dict]:
    if not genre:
        return None
    g = genre.lower().strip()
    if g in GENRE_STRUCTURE_TEMPLATES:
        return GENRE_STRUCTURE_TEMPLATES[g]
    if g in GENRE_ALIASES_FOR_TEMPLATES:
        return GENRE_STRUCTURE_TEMPLATES.get(GENRE_ALIASES_FOR_TEMPLATES[g])
    for key in GENRE_STRUCTURE_TEMPLATES:
        if key in g or g in key:
            return GENRE_STRUCTURE_TEMPLATES[key]
    return None


def _build_genre_instruction(genre: Optional[str], task: str = "optimize") -> str:
    template = _resolve_genre_template(genre)
    if not template:
        return ""
    avoid_text = template.get("avoid", "")
    if task == "optimize":
        parts = [
            f"\n\nCRITICAL GENRE CONSTRAINT — {genre.upper()}:",
            f"This song MUST follow {genre} conventions. Do NOT write a generic pop ballad.",
            f"- Required structure: {template['structure']}",
            f"- Section markers: {template['sections']}",
            f"- Instrumentation: {template['instrumentation']}",
            f"- Vocal style: {template['vocal_style']}",
            f"- BPM range: {template['bpm_range'][0]}–{template['bpm_range'][1]} (choose within this range)",
            f"- The 'song_structure' field MUST match the required structure above.",
            f"- The 'prompt' field MUST specify the {genre} instrumentation and texture explicitly.",
        ]
        if avoid_text:
            parts.append(f"- EVITAR / DO NOT INCLUDE: {avoid_text}")
            parts.append("- The 'prompt' field MUST end with an 'EVITAR:' line listing these forbidden elements.")
        return "\n".join(parts)
    else:
        parts = [
            f"\n\nCRITICAL GENRE CONSTRAINT — {genre.upper()}:",
            f"You are writing a {genre} song, NOT a generic pop ballad.",
            f"- Required section markers: {template['sections']}",
            f"- Lyrics style: {template['lyrics_style']}",
            f"- Vocal style: {template['vocal_style']}",
            f"- Use EXACTLY these section markers — do NOT substitute generic [Pre-Chorus]/[Bridge] if they don't belong in {genre}.",
            f"- Total lyrics length: match the genre convention ({'short, 8-16 lines' if genre == 'electronic' else 'standard verse-chorus length'}).",
        ]
        if avoid_text:
            parts.append(f"- EVITAR en la letra: {avoid_text}")
        return "\n".join(parts)


MOOD_GENRE_OVERRIDES = {
    ("melancholic", "rock"): "Alt-rock/grunge vibe: minor key, slow-burn dynamics, quiet verse → explosive chorus, angsty lyrics, distorted guitars swell on chorus. Think Nirvana, Radiohead, Smashing Pumpkins.",
    ("melancholic", "hip-hop"): "Lo-fi/emotional hip-hop: introspective lyrics, sparse beat, vinyl crackle, pitched-down soul sample, heavy sub-bass, slow flow. Think Earl Sweatshirt, Joji, XXXTentacion.",
    ("melancholic", "electronic"): "Ambient/downtempo: slow BPM (90-110), minor key synth pads, reverb-drenched vocals (if any), no big drops — gradual builds and dissolves. Think Bonobo, Burial, Tycho.",
    ("melancholic", "folk"): "Sparse fingerpicked acoustic, minor key, breathy vocal, cello drone, themes of loss and nature. Think Bon Iver, Sufjan Stevens, Nick Drake.",
    ("melancholic", "jazz"): "Ballad tempo (50-80 BPM), minor key, brushed drums, sparse piano chords, yearning melody, space and silence. Think Bill Evans, Chet Baker.",
    ("melancholic", "country"): "Weeping steel guitar, slow tempo, heartbreak narrative, simple AAB verses, tear-in-your-beer lyrics. Think George Jones, Hank Williams.",
    ("melancholic", "r&b"): "Slow jam: 60-80 BPM, minor key, deep bass, Rhodes piano, vulnerable vocal delivery, falsetto on chorus. Think Frank Ocean, The Weeknd, SZA.",
    ("melancholic", "metal"): "Doom/progressive: slow-heavy riffs, dark atmosphere, clean verses → harsh chorus, minor key, epic dynamics. Think Opeth, Katatonia, Type O Negative.",
    ("melancholic", "latin"): "Bolero/bachata: romantic longing, minor key guitar arpeggios, gentle percussion, passionate vocal with broken-heart lyrics. Think Romeo Santos, Juan Luis Guerra.",
    ("melancholic", "indie"): "Bedroom/slowcore: lo-fi, reverb, droning guitars, mumbled intimate vocal, minimalist arrangement. Think Alex G, (Sandy) Alex G, Phoebe Bridgers.",
    ("energetic", "rock"): "Punk/hard-rock: fast BPM (150+), power chords, driving rhythm, short punchy verses, anthemic chorus, guitar solo. NO ballad elements. Think AC/DC, Ramones.",
    ("energetic", "hip-hop"): "Trap/bangers: fast hi-hats, 808 drops, aggressive flow, hype ad-libs, chant-style hook, high BPM (130+). Think Travis Scott, DMX, Lil Jon.",
    ("energetic", "electronic"): "Peak-time banger: 128-140 BPM, big buildup → massive drop, supersaw leads, sidechained everything, festival energy. Think Martin Garrix, Skrillex.",
    ("energetic", "folk"): "Up-tempo folk-rock: fast strumming, driving rhythm, foot-stomping energy, harmonica solos, sing-along chorus. Think The Pogues, Dropkick Murphys.",
    ("energetic", "jazz"): "Bebop/hard-bop: fast tempo (180+), driving swing, rapid solos, complex harmony, intense rhythm section interaction. Think Art Blakey, John Coltrane.",
    ("energetic", "country"): "Up-tempo hoedown/CMT: driving rhythm, fiddle leads, boom-clap drums, party/road-trip lyrics, big chorus. Think Luke Bryan, Brad Paisley.",
    ("energetic", "latin"): "Reggaeton/salsa dura: driving percussion, brass stabs, high BPM (140+), call-and-response vocals, dance-floor energy. Think Bad Bunny, Marc Anthony.",
    ("energetic", "r&b"): "Funk/dance-R&B: groove-heavy bass, syncopated drums, horn stabs, 100-120 BPM, party lyrics, James Brown energy. Think Bruno Mars, Anderson .Paak.",
    ("energetic", "metal"): "Thrash/speed: 160+ BPM, blast beats, relentless riffs, aggressive vocals, short songs, mosh-pit energy. Think Slayer, Metallica (early).",
    ("dark", "electronic"): "Dark techno/industrial: 130-145 BPM, minor key, distorted kicks, atonal synth stabs, no melody, atmospheric dread. Think Surgeon, Blawan.",
    ("dark", "hip-hop"): "Horrorcore/dark trap: minor key, eerie melody, distorted 808s, horror-film samples, aggressive paranoid lyrics. Think $uicideboy$, Three 6 Mafia.",
    ("dark", "rock"): "Goth/doom: minor key, slow-heavy riffs, atmospheric reverb, brooding vocals, dark themes. Think Black Sabbath, Bauhaus, Type O Negative.",
    ("dark", "metal"): "Black/death: extreme tempo or crushing doom, tremolo picking, harsh vocals, anti-religious/existential themes, cold atmosphere. Think Darkthrone, Death.",
    ("romantic", "latin"): "Bachata/salsa romántica: sensual groove, smooth vocal, romantic lyrics, guitar/piano arpeggios, gentle percussion. Think Romeo Santos, Marc Anthony.",
    ("romantic", "r&b"): "Slow jam: intimate vocal, sensual lyrics, Rhodes piano, deep bass groove, falsetto, bedroom production. Think The Weeknd, SZA, Daniel Caesar.",
    ("romantic", "folk"): "Tender fingerpicked acoustic, soft vocal, love-letter lyrics, gentle harmony, minimal percussion. Think Iron & Wine, José González.",
    ("romantic", "jazz"): "Vocal jazz ballad: smooth delivery, romantic standards, piano trio, swing ballad feel. Think Ella Fitzgerald, Billie Holiday.",
}


def _build_mood_genre_override(mood: Optional[str], genre: Optional[str]) -> str:
    if not mood or not genre:
        return ""
    resolved_genre = genre
    template_genre = _resolve_genre_template(genre)
    if not template_genre:
        g = genre.lower().strip()
        if g in GENRE_ALIASES_FOR_TEMPLATES:
            resolved_genre = GENRE_ALIASES_FOR_TEMPLATES[g]
    override = MOOD_GENRE_OVERRIDES.get((mood, resolved_genre))
    if override:
        return f"\n\nMOOD-GENRE COMBINATION OVERRIDE ({mood} + {genre}):\n{override}\nApply this specific vibe to the output. This takes priority over generic genre defaults."
    return ""


FEATURE_DESCRIPTOR_MAP = {
    "danceability": [(0.8, "highly danceable"), (0.6, "danceable"), (0.4, "moderately danceable"), (0.0, "minimal danceability")],
    "energy": [(0.8, "high-energy"), (0.6, "moderate-energy"), (0.4, "low-energy"), (0.0, "very low-energy")],
    "valence": [(0.7, "positive/bright"), (0.5, "neutral mood"), (0.3, "melancholic/dark"), (0.0, "very dark/sad")],
    "speechiness": [(0.5, "speech-heavy/rap-oriented"), (0.2, "some vocal presence"), (0.0, "minimal speech")],
    "acousticness": [(0.7, "largely acoustic"), (0.4, "some acoustic elements"), (0.0, "fully electronic/synthetic")],
    "instrumentalness": [(0.7, "mostly instrumental"), (0.3, "some instrumental passages"), (0.0, "vocal-driven")],
    "liveness": [(0.7, "live performance feel"), (0.3, "some live ambiance"), (0.0, "studio production")],
}


def _describe_feature(name: str, value: float) -> str:
    for threshold, label in FEATURE_DESCRIPTOR_MAP.get(name, []):
        if value >= threshold:
            return label
    return ""


def _describe_track(t: dict) -> str:
    parts = []
    genre = t.get("track_genre", "")
    if genre:
        parts.append(genre)
    tempo = t.get("tempo", 120)
    parts.append(f"{tempo:.0f}BPM")
    key = t.get("key")
    mode = t.get("mode")
    if key is not None and mode is not None:
        key_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        key_str = key_names[key % 12] if key < 12 else str(key)
        mode_str = MODE_LABELS.get(mode, "unknown")
        parts.append(f"{key_str} {mode_str}")
    for feat in ["danceability", "energy", "valence", "acousticness", "instrumentalness"]:
        val = t.get(feat)
        if val is not None:
            desc = _describe_feature(feat, val)
            if desc:
                parts.append(desc)
    loudness = t.get("loudness", -6)
    if loudness < -10:
        parts.append("quiet/mellow mix")
    elif loudness > -5:
        parts.append("loud/punchy mix")
    pop = t.get("popularity", 0)
    if pop > 70:
        parts.append(f"hit (pop {pop})")
    return ", ".join(parts)


@dataclass
class ModelProfile:
    model_id: str
    display_name: str = ""
    family: str = ""
    context_window: int = 4096
    max_output_tokens: int = 2048
    optimal_temperature: float = 0.6
    json_reliability: str = "low"
    instruction_following: str = "low"
    needs_json_reinforcement: bool = True
    needs_simple_prompts: bool = True
    supports_system_prompt: bool = True
    tested_at: str = ""
    auto_detected: bool = False


FAMILY_DETECTION = [
    ("qwen", "qwen"),
    ("llama", "llama"),
    ("mistral", "mistral"),
    ("mixtral", "mistral"),
    ("phi", "phi"),
    ("gemma", "gemma"),
    ("deepseek", "deepseek"),
    ("yi-", "yi"),
    ("starcoder", "starcoder"),
    ("codellama", "codellama"),
    ("code-llama", "codellama"),
]


def _detect_family(model_id: str) -> str:
    mid = model_id.lower()
    for keyword, family in FAMILY_DETECTION:
        if keyword in mid:
            return family
    return "unknown"


SYSTEM_PROMPT_OPTIMIZE_FULL = """Eres un productor musical experto. Tu única tarea es transformar la descripción del usuario en un prompt musical TÉCNICO y CONCISO para ACE-Step (generador de audio), basándote en las canciones de referencia proporcionadas.

El campo 'prompt' debe ser TÉCNICO y CONCISO — es lo que recibe ACE-Step directamente. No escribas prosa poética.

Formato OBLIGATORIO del campo 'prompt':
"[Género subgénero], [BPM] BPM, [key mode], [drum pattern], [bass type], [main instruments], [production effects], [vocal style], [texture/atmosphere], EVITAR: [elements]"

Ejemplos:
- Hip-hop: "Trap hip-hop, 140 BPM, F# minor, rapid trap hi-hats with 808 sub-bass, snare on 2&4, synth pad stabs, male vocal aggressive flow, vinyl crackle texture, phone filter on intro, EVITAR: pre-chorus, pop melody, autotune"
- Rock: "Alt-rock grunge, 155 BPM, E minor, distorted power chords, driving drum kit with crash cymbals, heavy bass, guitar solo bridge, male vocal gritty belting, loud-anthemic chorus, EVITAR: autotune, synth pads, pop harmonies"
- Latin: "Reggaeton perreo, 96 BPM, F# minor, dembow pattern with syncopated hi-hats, distorted 808 slides, atmospheric intro, Spanish male vocals melodic flow, phone filter intro vinyl crackle, EVITAR: pop drums, boy band harmonies, English lyrics"
- Electronic: "Deep house, 124 BPM, A minor, 4-on-floor kick with sidechained bass, synth stabs, arpeggiated pad, vocal chop hooks, reverb-drenched drops, EVITAR: full verses, acoustic guitar, ballad dynamics"
- Folk: "Indie folk, 98 BPM, G major, fingerpicked acoustic guitar, upright bass, light tambourine, warm close-mic vocal, harmony chorus, cello drone, EVITAR: electronic beats, autotune, boy band vocals"

REGLA CRÍTICA: Cada género tiene su propia estructura e instrumentación. Un tema de hip-hop NO tiene pre-chorus ni bridge — tiene versos de 16 compases y hooks de 4. Un tema de rock NO tiene pre-chorus — tiene riff intro, versos, chorus, y guitar solo. Un tema de blues usa forma AAB de 12 compases. Un tema de electronic tiene builds y drops, no versos completos. RESPETA la estructura del género.

El campo 'prompt' DEBE incluir una línea "EVITAR:" al final listando los elementos prohibidos según el género.

Reglas para los parámetros:
- BPM: basado en el promedio de las referencias (±5 BPM) Y dentro del rango típico del género. No inventes un BPM arbitrario.
- Key/scale: basa la decisión en el 'key' y 'mode' de las referencias. Si mayoría mode=1 → major, mode=0 → minor. Elige la key más frecuente.
- Mood: selecciona el mood más apropiado de la lista de moods disponibles que mejor represente el vibe del prompt.
- Song structure: describe la estructura EXACTA del género en formato de compases con marcadores de sección.

Responde SOLO con JSON válido — nada de markdown, código, o texto fuera del JSON:
{{"prompt": "...", "bpm": 120, "key_scale": "C major", "time_signature": "4/4", "song_structure": "...", "mood": "..."}}"""

SYSTEM_PROMPT_OPTIMIZE_SIMPLE = """Eres un productor musical. Transforma la descripción en un prompt musical detallado basándote en las referencias.

Incluye: género específico, mood descriptivo, instrumentación, textura, tipo de voz.
BPM: promedio de las referencias ±5. Key: basada en mode de las referencias.

Responde SOLO con JSON:
{{"prompt": "...", "bpm": 120, "key_scale": "C major", "time_signature": "4/4", "song_structure": "...", "mood": "..."}}"""

SYSTEM_PROMPT_COMPOSE_FULL = """Eres un compositor de hits internacionales. Tu única tarea es escribir una letra ORIGINAL para la canción descrita.

Analiza el ESTILO de las canciones de referencia proporcionadas — su estructura, ritmo silábico, temas, registro emocional — pero NUNCA copies sus letras. Escribe algo nuevo y original que capture el mismo espíritu.

REGLA CRÍTICA: La estructura de la letra DEBE coincidir con el género. NO uses la misma estructura genérica de pop para todos los géneros:
- HIP-HOP: Versos de 16 compases con rimas densas, hook de 4 compases repetido. SIN pre-chorus ni bridge.
- ROCK: Verso → Coro → Verso → Coro → Solo → Coro. El coro es anthemic y corto. Sin pre-chorus.
- ELECTRONIC: Letras MÍNIMAS — frases cortas, vocal chops. Drops son instrumentales. 8-16 líneas total, NO 40.
- BLUES: Forma AAB de 12 compases. Primera línea → repite → responde. Sin chorus/bridge tradicional.
- METAL: Versos agresivos, coro potente. Bridge = solo instrumental. Lenguaje oscuro/violento.
- R&B: Pre-chorus building, coro melódico y lush, bridge con vocal runs.
- JAZZ: Forma AABA, sofisticada, con espacio para la música. Sin hooks pop repetitivos.
- COUNTRY: Narrativo, verso largo, coro cantable. Lenguaje concreto (camiones, caminos, whiskey).
- FOLK: Storytelling poético, verso largo, coro reflexivo. Imágenes orgánicas.
- LATIN: Rítmico y bailable, coro pegajoso. Break de percusión en el bridge.
- REGGAE: One-drop, verso → coro → dub section (bass-heavy) → coro.
- SOUL: Pre-chorus building, coro soaring, bridge con vocal showcase.
- INDIE: Verso íntimo, coro atmospheric (no necessarily catchy), bridge textural.

PROCESO DE COMPOSICIÓN (obligatorio):

PASO 1 — CONCEPTO: Antes de escribir ninguna línea, define tu concepto en 1 frase mental. NO lo escribas en la letra. Ejemplos de BUENOS conceptos: "Una llamada a las 3AM que cambia todo", "El sonido del asfalto cuando llueve y no tienes dónde ir", "La promesa que le hiciste a tu hermano menor". Ejemplos de MALOS conceptos: "Luchar por tus sueños", "La vida en la ciudad", "Ser libre".

PASO 2 — IMÁGENES ANCLA: Cada verso necesita al menos 1 imagen sensorial específica (visual, táctil, olfativa, auditiva). NO uses abstracciones: "corazón roto", "alma vacía", "noche oscura", "caminar solo". SÍ usa: "el olor a gasolina en tus manos", "el timbre de la puerta oxidado", "la firma de tu madre en la carta que nunca mandó".

PASO 3 — CORO CON GANCHO: El coro debe tener 1 frase pegadiza que se repita (el "hook"). Máximo 6 líneas. Cada línea del coro debe poder cantarse en la misma melodía. El hook es la frase que alguien tararea después de escuchar la canción una vez.

PASO 4 — PROGRESIÓN: La letra debe avanzar. Verso 1 = plantea la situación. Verso 2 = complica o profundiza. NO repitas las mismas ideas en ambos versos. El coro puede repetirse pero cada vez resuena diferente por el contexto.

REGLAS DE ORO:
- PROHIBIDO: "running on empty", "chasing dreams", "breaking free", "light in the dark", "standing tall", "never give up", "heart of gold", "tears fall down", "hold on", "rise above", "shine bright"
- PROHIBIDO: Nombrar emociones directamente ("I feel sad", "I'm so lonely", "I'm angry"). MUESTRA, NO DIGAS. En vez de "estoy triste" → "las sobras del bar cierran antes de que termine mi copa"
- PROHIBIDO: Versos que son listas de observaciones sin conexión narrativa
- OBLIGATORIO: Al menos 1 imagen inesperada por verso (algo que no esperarías en ese género)
- OBLIGATORIO: Rimas internas o asonancias, no solo rimas al final de línea
- OBLIGATORIO: El último verso debe tener un giro o revelación que cambie el significado del coro

Reglas de formato:
- Usa los marcadores de sección EXACTOS que corresponden al género
- El chorus/hook debe ser pegadizo y memorable
- Mantén el ritmo silábico y la métrica del estilo referenciado
- Para dueto: usa [Male] y [Female] como prefijos en las líneas
- Para backing vocals: usa [Backing] o [Harmony] tags
- Escribe en el idioma solicitado

Las referencias están etiquetadas con su rol:
- IDENTIDAD PRINCIPAL (60%): Define la identidad sónica — estructura, ritmo, flujo. Sigue esta referencia como base.
- CONTRASTE/COMPLEMENTO (30%): Aporta un elemento diferente que hace el tema único. Incorpora sutilmente.
- ELEMENTO SORPRESA (10%): Un toque inesperado. Incorpóralo como textura o detalle menor.

Responde SOLO con la letra, sin explicaciones, sin JSON, sin markdown."""

SYSTEM_PROMPT_COMPOSE_SIMPLE = """Escribe una letra ORIGINAL para esta canción. Inspírate en las referencias pero NO las copies.

Usa los marcadores de sección del género (NO todos los géneros usan [Pre-Chorus] o [Bridge]). Hip-hop: [Verse]+[Hook], Rock: [Verse]+[Chorus]+[Solo], Electronic: [Build-Up]+[Drop]+[Breakdown], Blues: [Verse AAB].
Para dueto: [Male]/[Female]. Para backing: [Backing].

PROHIBIDO: "running on empty", "chasing dreams", "breaking free", "light in the dark", "standing tall", "never give up", "heart of gold", "tears fall down"
PROHIBIDO: Nombrar emociones directamente. MUESTRA, NO DIGAS.
OBLIGATORIO: 1 imagen sensorial específica por verso (olor, tacto, sonido — no abstracciones).
OBLIGATORIO: El coro tiene 1 frase hook que se repite.
OBLIGATORIO: Verso 2 complica/profundiza lo del Verso 1, no repite.

Las refs están etiquetadas: IDENTIDAD PRINCIPAL (base), CONTRASTE (elemento diferente), ELEMENTO SORPRESA (toque inesperado).

Responde SOLO con la letra, nada más."""

JSON_REINFORCEMENT = "\n\nCRITICAL: Respond ONLY with valid JSON. No markdown code blocks, no ```json```, no text before or after the JSON object. Just the raw JSON."


class LMStudioClient:
    def __init__(self):
        self.base_url = settings.LM_STUDIO_BASE_URL
        self.api_key = settings.LM_STUDIO_API_KEY
        self._available = False
        self._model_id: Optional[str] = None
        self._all_models: list[dict] = []
        self._profiles: dict[str, ModelProfile] = {}
        self._active_profile: Optional[ModelProfile] = None

    def is_available(self) -> bool:
        return self._available

    def get_active_profile(self) -> Optional[ModelProfile]:
        return self._active_profile

    def get_all_profiles(self) -> dict[str, ModelProfile]:
        return self._profiles

    async def check_availability(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/models")
                if resp.status_code == 200:
                    data = resp.json()
                    models = data.get("data", [])
                    if models:
                        self._all_models = models
                        self._model_id = models[0]["id"]
                        self._available = True
                        logger.info(f"LM Studio available - model: {self._model_id}")
                        return True
        except Exception as e:
            logger.warning(f"LM Studio not available: {e}")
        self._available = False
        return False

    def load_profiles(self) -> dict[str, ModelProfile]:
        profiles = {}
        if PROFILES_PATH.exists():
            try:
                raw = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
                for mid, pdata in raw.get("profiles", {}).items():
                    profiles[mid] = ModelProfile(
                        model_id=mid,
                        display_name=pdata.get("display_name", mid),
                        family=pdata.get("family", "unknown"),
                        context_window=pdata.get("context_window", 4096),
                        max_output_tokens=pdata.get("max_output_tokens", 2048),
                        optimal_temperature=pdata.get("optimal_temperature", 0.6),
                        json_reliability=pdata.get("json_reliability", "low"),
                        instruction_following=pdata.get("instruction_following", "low"),
                        needs_json_reinforcement=pdata.get("needs_json_reinforcement", True),
                        needs_simple_prompts=pdata.get("needs_simple_prompts", True),
                        supports_system_prompt=pdata.get("supports_system_prompt", True),
                        tested_at=pdata.get("tested_at", ""),
                        auto_detected=pdata.get("auto_detected", False),
                    )
                logger.info(f"Loaded {len(profiles)} model profiles from {PROFILES_PATH}")
            except Exception as e:
                logger.warning(f"Failed to load model profiles: {e}")
        self._profiles = profiles
        return profiles

    def save_profiles(self):
        raw = {"profiles": {}, "last_scan": datetime.now().isoformat()}
        if PROFILES_PATH.exists():
            try:
                existing = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
                raw["auto_detect_settings"] = existing.get("auto_detect_settings", {})
            except Exception:
                pass
        for mid, p in self._profiles.items():
            raw["profiles"][mid] = asdict(p)
        PROFILES_PATH.parent.mkdir(parents=True, exist_ok=True)
        PROFILES_PATH.write_text(json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info(f"Saved {len(self._profiles)} model profiles to {PROFILES_PATH}")

    async def scan_and_build_profiles(self) -> list[str]:
        if not self._all_models:
            await self.check_availability()
        if not self._all_models:
            return []

        self.load_profiles()
        new_profiles = []
        for m in self._all_models:
            mid = m.get("id", "")
            if not mid:
                continue
            if mid not in self._profiles:
                profile = await self._auto_detect_profile(mid)
                self._profiles[mid] = profile
                new_profiles.append(mid)
                logger.info(f"Auto-detected profile for model: {mid} (family={profile.family}, json={profile.json_reliability})")

        if new_profiles:
            self.save_profiles()

        if self._model_id and self._model_id in self._profiles:
            self._active_profile = self._profiles[self._model_id]
            logger.info(f"Active model profile: {self._model_id} (family={self._active_profile.family})")
        elif self._model_id:
            self._active_profile = self._create_default_profile(self._model_id)
            logger.info(f"Active model: {self._model_id} (using default profile)")

        return new_profiles

    async def _auto_detect_profile(self, model_id: str) -> ModelProfile:
        family = _detect_family(model_id)
        base = self._get_family_defaults(family)

        profile = ModelProfile(
            model_id=model_id,
            display_name=base.get("display_name_prefix", "Unknown"),
            family=family,
            context_window=base.get("context_window", 4096),
            max_output_tokens=base.get("max_output_tokens", 2048),
            optimal_temperature=base.get("optimal_temperature", 0.6),
            json_reliability=base.get("json_reliability", "low"),
            instruction_following=base.get("instruction_following", "low"),
            needs_json_reinforcement=base.get("needs_json_reinforcement", True),
            needs_simple_prompts=base.get("needs_simple_prompts", True),
            supports_system_prompt=base.get("supports_system_prompt", True),
            tested_at=datetime.now().isoformat(),
            auto_detected=True,
        )

        test_result = await self._run_test_prompt(model_id)
        if test_result:
            profile.json_reliability = test_result["json_reliability"]
            profile.instruction_following = test_result["instruction_following"]
            if test_result["json_reliability"] == "high":
                profile.needs_json_reinforcement = False
            elif test_result["json_reliability"] == "low":
                profile.needs_json_reinforcement = True
                profile.needs_simple_prompts = True
            logger.info(f"Test prompt result for {model_id}: json={test_result['json_reliability']}, instruct={test_result['instruction_following']}")

        return profile

    def _create_default_profile(self, model_id: str) -> ModelProfile:
        family = _detect_family(model_id)
        base = self._get_family_defaults(family)
        return ModelProfile(
            model_id=model_id,
            display_name=base.get("display_name_prefix", "Unknown"),
            family=family,
            context_window=base.get("context_window", 4096),
            max_output_tokens=base.get("max_output_tokens", 2048),
            optimal_temperature=base.get("optimal_temperature", 0.6),
            json_reliability=base.get("json_reliability", "low"),
            instruction_following=base.get("instruction_following", "low"),
            needs_json_reinforcement=base.get("needs_json_reinforcement", True),
            needs_simple_prompts=base.get("needs_simple_prompts", True),
            supports_system_prompt=base.get("supports_system_prompt", True),
            tested_at=datetime.now().isoformat(),
            auto_detected=False,
        )

    def _get_family_defaults(self, family: str) -> dict:
        if PROFILES_PATH.exists():
            try:
                raw = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
                families = raw.get("auto_detect_settings", {}).get("families", {})
                if family in families:
                    return families[family]
            except Exception:
                pass
        defaults_map = {
            "qwen": {"display_name_prefix": "Qwen", "context_window": 32768, "max_output_tokens": 4096, "optimal_temperature": 0.6, "json_reliability": "high", "instruction_following": "high", "needs_json_reinforcement": False, "needs_simple_prompts": False, "supports_system_prompt": True},
            "llama": {"display_name_prefix": "LLaMA", "context_window": 8192, "max_output_tokens": 4096, "optimal_temperature": 0.6, "json_reliability": "medium", "instruction_following": "high", "needs_json_reinforcement": True, "needs_simple_prompts": False, "supports_system_prompt": True},
            "mistral": {"display_name_prefix": "Mistral", "context_window": 32768, "max_output_tokens": 4096, "optimal_temperature": 0.6, "json_reliability": "high", "instruction_following": "high", "needs_json_reinforcement": False, "needs_simple_prompts": False, "supports_system_prompt": True},
            "phi": {"display_name_prefix": "Phi", "context_window": 4096, "max_output_tokens": 2048, "optimal_temperature": 0.4, "json_reliability": "medium", "instruction_following": "medium", "needs_json_reinforcement": True, "needs_simple_prompts": True, "supports_system_prompt": True},
            "gemma": {"display_name_prefix": "Gemma", "context_window": 8192, "max_output_tokens": 2048, "optimal_temperature": 0.5, "json_reliability": "medium", "instruction_following": "medium", "needs_json_reinforcement": True, "needs_simple_prompts": True, "supports_system_prompt": True},
            "deepseek": {"display_name_prefix": "DeepSeek", "context_window": 32768, "max_output_tokens": 4096, "optimal_temperature": 0.5, "json_reliability": "high", "instruction_following": "high", "needs_json_reinforcement": False, "needs_simple_prompts": False, "supports_system_prompt": True},
        }
        return defaults_map.get(family, {"display_name_prefix": "Unknown", "context_window": 4096, "max_output_tokens": 2048, "optimal_temperature": 0.6, "json_reliability": "low", "instruction_following": "low", "needs_json_reinforcement": True, "needs_simple_prompts": True, "supports_system_prompt": True})

    async def _run_test_prompt(self, model_id: str) -> Optional[dict]:
        test_prompt = 'Respond with ONLY a JSON object: {"status": "ok", "number": 42, "words": ["hello", "world"]}. No other text.'
        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": test_prompt}],
            "max_tokens": 200,
            "temperature": 0.1,
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                resp.raise_for_status()
                text = resp.json()["choices"][0]["message"]["content"].strip()

                json_ok = False
                if text.startswith("{"):
                    try:
                        parsed = json.loads(text)
                        if "status" in parsed and "number" in parsed:
                            json_ok = True
                    except json.JSONDecodeError:
                        pass
                if not json_ok and "```" in text:
                    start = text.find("{")
                    end = text.rfind("}")
                    if start >= 0 and end > start:
                        try:
                            parsed = json.loads(text[start:end + 1])
                            if "status" in parsed:
                                json_ok = True
                        except json.JSONDecodeError:
                            pass

                if json_ok:
                    json_rel = "high"
                    instruct = "high"
                elif "{" in text and "status" in text:
                    json_rel = "medium"
                    instruct = "medium"
                else:
                    json_rel = "low"
                    instruct = "low"

                return {"json_reliability": json_rel, "instruction_following": instruct}
        except Exception as e:
            logger.warning(f"Test prompt failed for {model_id}: {e}")
            return None

    def _adapt_system_prompt(self, base_prompt: str, is_json_response: bool = True) -> str:
        profile = self._active_profile
        if not profile:
            return base_prompt

        prompt = base_prompt
        if profile.needs_simple_prompts:
            if base_prompt == SYSTEM_PROMPT_OPTIMIZE_FULL:
                prompt = SYSTEM_PROMPT_OPTIMIZE_SIMPLE
            elif base_prompt == SYSTEM_PROMPT_COMPOSE_FULL:
                prompt = SYSTEM_PROMPT_COMPOSE_SIMPLE

        if is_json_response and profile.needs_json_reinforcement:
            prompt += JSON_REINFORCEMENT

        if not profile.supports_system_prompt:
            return prompt

        return prompt

    def _get_max_tokens(self, task: str = "optimize") -> int:
        profile = self._active_profile
        base = profile.max_output_tokens if profile else 2048
        if task == "optimize":
            return min(base, 1500)
        elif task == "compose":
            return min(base, 3000)
        return base

    def _get_temperature(self, task: str = "optimize") -> float:
        profile = self._active_profile
        base = profile.optimal_temperature if profile else 0.6
        if task == "compose":
            return min(1.0, base + 0.2)
        return base

    async def optimize_prompt(
        self,
        reference_tracks: list[dict],
        user_prompt: str,
        genre: Optional[str] = None,
        mood: Optional[str] = None,
        voice_type: Optional[str] = None,
        hit_profile: Optional[dict] = None,
        available_moods: Optional[list[str]] = None,
        surprise_element: Optional[str] = None,
    ) -> dict:
        default_result = {
            "prompt": user_prompt, "bpm": 120, "key_scale": "C major",
            "time_signature": "4/4", "song_structure": "", "mood": mood or "",
        }
        if not self._available:
            return default_result

        system_prompt = self._adapt_system_prompt(SYSTEM_PROMPT_OPTIMIZE_FULL, is_json_response=True)

        genre_instruction = _build_genre_instruction(genre, task="optimize")
        if genre_instruction:
            system_prompt += genre_instruction

        mood_genre_override = _build_mood_genre_override(mood, genre)
        if mood_genre_override:
            system_prompt += mood_genre_override

        user_parts = [f"User prompt: {user_prompt}"]
        if genre:
            user_parts.append(f"Genre: {genre}")
        if mood:
            user_parts.append(f"User mood preference: {mood}")
        if voice_type and voice_type != "instrumental":
            voice_map = {
                "male": "male vocalist",
                "female": "female vocalist",
                "duet": "male and female duet",
            }
            user_parts.append(f"Voice: {voice_map.get(voice_type, voice_type)}")
        elif voice_type == "instrumental":
            user_parts.append("This track is INSTRUMENTAL — no vocals.")

        if available_moods:
            user_parts.append(f"Available moods (select one for the 'mood' field): {', '.join(available_moods)}")

        if hit_profile:
            p = hit_profile
            user_parts.append(
                f"Genre hit profile ({p.get('sample_size', 0)} popular tracks): "
                f"danceability={p.get('avg_danceability', 0.5):.2f}, "
                f"energy={p.get('avg_energy', 0.5):.2f}, "
                f"valence={p.get('avg_valence', 0.5):.2f}, "
                f"avg tempo={p.get('avg_tempo', 120):.0f}BPM, "
                f"avg loudness={p.get('avg_loudness', -8):.1f}dB, "
                f"acousticness={p.get('avg_acousticness', 0):.2f}, "
                f"instrumentalness={p.get('avg_instrumentalness', 0):.2f}"
            )

        if reference_tracks:
            ref_lines = []
            for i, t in enumerate(reference_tracks[:10], 1):
                desc = _describe_track(t)
                role = t.get("ref_role", "primary")
                role_label = {"primary": "PRIMARY IDENTITY", "contrast": "CROSS-GENRE CONTRAST", "surprise": "SURPRISE ELEMENT"}.get(role, "REFERENCE")
                weight = int(t.get("ref_weight", 0.60) * 100)
                ref_lines.append(f" {i}. [{role_label} — {weight}%] \"{t.get('track_name', '?')}\" by {t.get('artist_name', '?')} ({t.get('track_genre', '?')}): {desc}")
            user_parts.append("Reference tracks from database:\n" + "\n".join(ref_lines))
            user_parts.append(
                "Use these reference tracks as sonic guides. PRIMARY tracks define the genre identity — follow their structure and sound. "
                "CONTRAST tracks provide a cross-genre element — incorporate subtly for uniqueness. "
                "SURPRISE tracks are an unexpected touch — use sparingly as a texture/detail. "
                "BPM should be within ±5 of the PRIMARY references' average. "
                "Key/scale should match the predominant mode of the PRIMARY references."
            )
        if surprise_element:
            user_parts.append(f"SURPRISE ELEMENT to incorporate subtly in the prompt: {surprise_element}")

        payload = {
            "model": self._model_id or "local-model",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "\n\n".join(user_parts)},
            ],
            "max_tokens": self._get_max_tokens("optimize"),
            "temperature": self._get_temperature("optimize"),
        }

        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"]
            logger.info(f"LM Studio optimize raw response: {text[:500]}")

            parsed = self._parse_json_response(text)
            return {
                "prompt": parsed.get("prompt", user_prompt),
                "bpm": parsed.get("bpm", 120),
                "key_scale": parsed.get("key_scale", "C major"),
                "time_signature": parsed.get("time_signature", "4/4"),
                "song_structure": parsed.get("song_structure", ""),
                "mood": parsed.get("mood", mood or ""),
                "_lm_raw_response": text,
                "_lm_parsed_response": parsed,
                "_lm_success": bool(parsed),
            }
        except Exception as e:
            logger.warning(f"LM Studio optimize_prompt failed: {e}")
            return default_result

    async def analyze_artist_voice(self, primary_lyrics: list[dict]) -> str:
        """
        PASO PREVIO a compose_lyrics.
        Analiza las letras del artista principal (ref_role='primary') y extrae
        su huella estilística como bloque de texto listo para insertar en el system prompt.
        Temperature muy baja — esto es análisis, no creación.
        """
        if not self._available or not primary_lyrics:
            return ""

        lyrics_text = "\n\n---\n\n".join([
            f"[{s.get('track', '?')} — {s.get('artist', '?')}]\n{s.get('text', '')[:600]}"
            for s in primary_lyrics[:3]
        ])

        system = (
            "You are a musicologist analyzing song lyrics. "
            "Your job is to extract precise stylistic patterns. "
            "Respond ONLY with the analysis in the exact format requested. No preamble."
        )
        user = f"""Analyze these lyrics and extract the artist's stylistic fingerprint.

LYRICS:
{lyrics_text}

Respond using EXACTLY this format (plain text, no JSON, no markdown):
WORDS_PER_LINE: <average number, e.g. 7>
RHYME: <AABB|ABAB|libre|mixto>
VOCABULARY: <10 most characteristic words, comma-separated>
THEMES: <3 recurring themes, comma-separated>
OBJECTS: <5 concrete physical objects the artist mentions, comma-separated>
VERBS: <8 dominant verbs, comma-separated>
STYLE: <directo|metafórico|narrativo|confesional>
POV: <primera|segunda|tercera>
TENSE: <pasado|presente|mixto>
NEVER: <3 things this artist NEVER does, pipe-separated, e.g.: usa metáforas de más de 4 palabras|menciona tecnología moderna|deja una emoción sin ancla física>
SIGNATURE: <1 example of a characteristic phrase construction, e.g.: "verb + concrete object + emotional consequence">"""

        payload = {
            "model": self._model_id or "local-model",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": 400,
            "temperature": 0.1,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                resp.raise_for_status()
                result = resp.json()["choices"][0]["message"]["content"].strip()
                logger.info(f"analyze_artist_voice result: {result[:200]}")
                return result
        except Exception as e:
            logger.warning(f"analyze_artist_voice failed: {e}")
            return ""

    async def compose_lyrics(
        self,
        prompt: str,
        reference_lyrics: list[dict],
        voice_type: Optional[str] = None,
        backing_vocals: Optional[str] = None,
        lyrics_language: Optional[str] = None,
        genre: Optional[str] = None,
        mood: Optional[str] = None,
        artist_fingerprint: str = "",
    ) -> str:
        if not self._available:
            raise RuntimeError("LM Studio is not available")

        system_prompt = self._adapt_system_prompt(SYSTEM_PROMPT_COMPOSE_FULL, is_json_response=False)

        genre_instruction = _build_genre_instruction(genre, task="compose")
        if genre_instruction:
            system_prompt += genre_instruction

        mood_genre_override = _build_mood_genre_override(mood, genre)
        if mood_genre_override:
            system_prompt += mood_genre_override

        # Fingerprint del artista principal: se inserta como restricción dura.
        # Tiene prioridad sobre las instrucciones genéricas de género porque viene
        # de las letras reales del artista, no de un template.
        if artist_fingerprint:
            system_prompt += (
                "\n\n═══ ARTIST VOICE FINGERPRINT — MANDATORY RULES ═══\n"
                "These rules are extracted from the PRIMARY artist's actual songs.\n"
                "They OVERRIDE any generic genre instruction above.\n\n"
                f"{artist_fingerprint}\n\n"
                "APPLY THE FINGERPRINT:\n"
                "- Use VOCABULARY and OBJECTS listed above — they are the artist's language.\n"
                "- Stay within WORDS_PER_LINE (±1 word max).\n"
                "- Follow the RHYME scheme exactly.\n"
                "- Write from the POV and TENSE specified.\n"
                "- The NEVER rules are absolute — any violation disqualifies the output.\n"
                "- Write AS this artist, not inspired by them.\n"
                "═══════════════════════════════════════════════════"
            )

        lang_map = {
            "es": "Spanish", "en": "English", "pt": "Portuguese",
            "ja": "Japanese", "zh": "Chinese", "fr": "French",
            "de": "German", "it": "Italian", "ko": "Korean",
        }
        lang_name = lang_map.get(lyrics_language or "en", lyrics_language or "English")

        user_parts = [f"Song description:\n{prompt}"]

        voice_section = ""
        if voice_type == "instrumental":
            return ""
        elif voice_type == "male":
            voice_section = "Male vocalist."
        elif voice_type == "female":
            voice_section = "Female vocalist."
        elif voice_type == "duet":
            voice_section = "Duet: use [Male] and [Female] prefix tags to mark who sings each line. Include harmonized sections."

        if voice_section:
            user_parts.append(f"Voice: {voice_section}")

        if backing_vocals and backing_vocals != "none":
            backing_map = {
                "harmony": "harmonized backing vocals",
                "call_response": "call-and-response backing vocals",
                "choir": "choir/choral backing vocals",
            }
            user_parts.append(f"Backing vocals: {backing_map.get(backing_vocals, backing_vocals)}. Mark with [Backing] or [Harmony] tags.")

        user_parts.append(f"Write lyrics in: {lang_name}")

        if reference_lyrics:
            lyrics_text_parts = []
            for s in reference_lyrics[:5]:
                sample_text = s.get("text", "")[:800]
                role = s.get("ref_role", "primary")
                weight = int(s.get("ref_weight", 0.60) * 100)
                role_label = {"primary": "IDENTIDAD PRINCIPAL", "contrast": "CONTRASTE/COMPLEMENTO", "surprise": "ELEMENTO SORPRESA"}.get(role, "REFERENCIA")
                lyrics_text_parts.append(f"[{role_label} — {weight}%] [{s.get('artist', '?')} - {s.get('track', '?')}]\n{sample_text}")
            user_parts.append("Reference lyrics (analyze their STYLE but do NOT copy):\n" + "\n---\n".join(lyrics_text_parts))
        user_parts.append(
            "INSTRUCCIONES DE COMPOSICIÓN:\n"
            "- La referencia PRIMARIA define la identidad sónica — estructura, ritmo, flujo\n"
            "- La referencia de CONTRASTE aporta un elemento diferente que hace el tema único\n"
            "- El ELEMENTO SORPRESA es un toque inesperado — incorpóralo sutilmente\n"
            "- DEFINE un concepto específico ANTES de escribir (no lo incluyas en la letra)\n"
            "- PROHIBIDO: clichés como 'running on empty', 'chasing dreams', 'breaking free', 'light in the dark'\n"
            "- PROHIBIDO: nombrar emociones directamente. MUESTRA con imágenes sensoriales, NO DIGAS\n"
            "- Cada verso necesita al menos 1 imagen concreta (olor, tacto, sonido)\n"
            "- El coro debe tener 1 frase hook pegadiza que se repita\n"
            "- Verso 2 debe profundizar o complicar Verso 1, NO repetir las mismas ideas\n"
            "- El último elemento debe tener un giro que cambie el significado del coro"
        )

        payload = {
            "model": self._model_id or "local-model",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "\n\n".join(user_parts)},
            ],
            "max_tokens": self._get_max_tokens("compose"),
            "temperature": self._get_temperature("compose"),
        }

        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            resp.raise_for_status()
            lyrics_text = resp.json()["choices"][0]["message"]["content"].strip()
            raw_lyrics = lyrics_text
            lyrics_text = lyrics_text.removeprefix("```").removeprefix("lyrics").removesuffix("```").strip()
        return {"lyrics": lyrics_text, "_lm_raw_response": raw_lyrics}

    def _parse_json_response(self, text: str) -> dict:
        text = text.strip()
        if not text:
            return {}

        # Strip markdown fences (```json ... ``` or ``` ... ```)
        if text.startswith("```"):
            lines = text.split("\n")
            start_idx = 1
            end_idx = len(lines)
            if lines[-1].strip().startswith("```"):
                end_idx = len(lines) - 1
            text = "\n".join(lines[start_idx:end_idx]).strip()

        # Also strip mid-text fences
        text = text.replace("```json", "").replace("```", "")

        # Strategy 1: try the whole text as JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Strategy 2: find the largest valid JSON object by trying each { position
        best = {}
        for i in range(len(text)):
            if text[i] != "{":
                continue
            for j in range(len(text), i, -1):
                candidate = text[i:j]
                try:
                    parsed = json.loads(candidate)
                    if len(str(parsed)) > len(str(best)):
                        best = parsed
                    break
                except json.JSONDecodeError:
                    continue

        return best

    async def craft_prompt(self, reference_package: dict, user_prompt: str,
                           genre: Optional[str] = None, mood: Optional[str] = None,
                           voice_type: Optional[str] = None,
                           backing_vocals: Optional[str] = None,
                           backing_vocal_style: Optional[str] = None,
                           lyrics_language: Optional[str] = None,
                           generate_lyrics: bool = False) -> dict:
        logger.warning("craft_prompt() is deprecated — use optimize_prompt() + compose_lyrics() instead")
        return {"prompt": user_prompt, "bpm": 120, "key_scale": "C major",
                "time_signature": "4/4", "lyrics_template": "", "song_structure": ""}

    async def generate_lyrics(self, theme: str, genre: Optional[str] = None,
                              style: Optional[str] = None, language: str = "english") -> str:
        if not self._available:
            raise RuntimeError("LM Studio is not available")

        system_prompt = "You are a hit songwriter. Write catchy, memorable lyrics.\nFormat: [Intro], [Verse 1], [Pre-Chorus], [Chorus], [Verse 2], [Bridge], [Chorus], [Outro]"

        user_parts = [f"Theme: {theme}"]
        if genre:
            user_parts.append(f"Genre: {genre}")
        if style:
            user_parts.append(f"Style: {style}")
        user_parts.append(f"Language: {language}")

        payload = {
            "model": self._model_id or "local-model",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "\n".join(user_parts) + "\n\nWrite hit song lyrics."},
            ],
            "max_tokens": self._get_max_tokens("compose"),
            "temperature": self._get_temperature("compose"),
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    async def analyze_hit_potential(self, prompt: str, audio_features: dict) -> dict:
        if not self._available:
            raise RuntimeError("LM Studio is not available")

        system_prompt = "You are a music industry analyst. Given a song's description and audio features, analyze its hit potential. Return JSON with: hit_score (0-1), hit_label, confidence (0-1), recommendations."

        payload = {
            "model": self._model_id or "local-model",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Prompt: {prompt}\n\nAudio Features: {audio_features}"},
            ],
            "max_tokens": 1000,
            "temperature": 0.3,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            resp.raise_for_status()
            return {"analysis": resp.json()["choices"][0]["message"]["content"]}

    async def get_loaded_models(self) -> list[dict]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/models")
                resp.raise_for_status()
                return resp.json().get("data", [])
        except Exception:
            return []

    def update_profile(self, model_id: str, updates: dict) -> Optional[ModelProfile]:
        if model_id not in self._profiles:
            return None
        profile = self._profiles[model_id]
        for key, value in updates.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        self.save_profiles()
        if self._model_id == model_id:
            self._active_profile = profile
        return profile
