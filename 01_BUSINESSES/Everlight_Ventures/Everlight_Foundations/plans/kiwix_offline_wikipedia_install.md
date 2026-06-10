# Kiwix Offline Wikipedia - Install Guide

**Source**: `05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/04_Self_Hosting_and_Offline_AI/wikipedia_offline_its_so_easy.txt` + `installing_your_own_offline_wikipedia.txt` + `critical_information_offline_kiwix_prepper.txt`
**Audience**: Lucrex (phone) + Forge (optional Oracle mirror)
**Time**: 45 minutes + download
**Cost**: $0. Storage only (up to 100 GB if you want the full set).

---

## Why this matters

1. **Grid-down resilience.** If Oracle E5 loses network, the Hive can still answer factual questions via local Wikipedia.
2. **Personal ops value.** Quick answers while driving or offline (no cell signal) on your nightly route.
3. **Costs nothing.** Kiwix is GPL software; the ZIM dumps are free downloads.

## On the phone (Android, Termux-friendly)

1. Install the Kiwix app via Play Store OR F-Droid (`Kiwix` package).
2. Open Kiwix, tap the library icon.
3. Download content. Recommended set for a 128 GB sdcard:

| Content | File | Size | Why |
|---|---|---|---|
| Wikipedia English (mini, no media) | `wikipedia_en_all_nopic` | ~16 GB | Full article text, no images, broadest signal |
| wikiHow English | `wikihow_en_all_maxi` | ~4 GB | Practical how-to for everything |
| iFixit English | `ifixit_en_all_maxi` | ~2 GB | Repair guides for phones, appliances, cars |
| Project Gutenberg Top 10K | `gutenberg_en_top_10k` | ~8 GB | Public-domain books |
| Medical Wikipedia | `wikimed_en_all_maxi` | ~6 GB | Drug/condition reference |

Direct URLs live at https://library.kiwix.org . Use the filters Language: English, then sort by date to get current dumps.

4. Once downloaded, Kiwix auto-indexes. Test by turning on Airplane mode and searching for "Stellar cryptocurrency".

## Optional: Oracle E5 mirror

Oracle already runs Blinko. Adding a Kiwix server lets other Hive agents query Wikipedia via HTTP.

```bash
# On Oracle E5
sudo dnf install -y kiwix-tools  # or build from source if not in dnf

# Download a small Wikipedia dump to Oracle
mkdir -p /home/opc/kiwix/zim
cd /home/opc/kiwix/zim
curl -LO https://download.kiwix.org/zim/wikipedia/wikipedia_en_all_nopic_2024-06.zim

# Start Kiwix server on port 8080 (internal only)
kiwix-serve --port=8080 --library /home/opc/kiwix/zim/*.zim &

# Test
curl http://127.0.0.1:8080/search?pattern=stellar+lumens | head -20
```

**Caution**: Oracle disk is at 94%. Do NOT mirror Kiwix to Oracle until disk is freed up. Phone-only for now.

## Integration with Hive RAG

Once `secondbrain_rag.py` is indexed, add a new stage that falls through to Kiwix for any question not answered from the workspace corpus. Add the Kiwix URL to `hive_llm_router.py` as a `stakes="research"` fallback option.

(Wiring note: this is a future step. Phone install first. Oracle mirror after disk cleanup.)

## Maintenance

- Kiwix dumps refresh ~quarterly. No hurry to update.
- ZIM files are self-contained; no background daemons needed on phone.
- On Oracle, `kiwix-serve` runs as a persistent process; wrap in systemd if you want auto-restart.

## Done criteria

- [ ] Kiwix app installed on phone
- [ ] Wikipedia-mini + wikiHow + iFixit ZIMs downloaded
- [ ] Airplane-mode test passes (returns an article)
- [ ] (Optional) Oracle kiwix-serve running on :8080
- [ ] (Optional) Hive router falls through to Kiwix for research stakes

## Resume keyword

`install kiwix` in a session with phone attention
