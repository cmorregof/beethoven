#!/usr/bin/env bash
# Descarga reproducible del corpus en corpus/raw/ (clones superficiales).
# Los commits exactos usados en la sesión del 2026-09-05 están en docs/CORPUS.md.
# Uso: bash scripts/download_corpus.sh
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)/corpus/raw"
mkdir -p "$ROOT/kern" "$ROOT/dcml" "$ROOT/_logs"
clone() {  # clone <github repo> <destino relativo a corpus/raw>
  local repo=$1 dest=$2
  if [ -d "$ROOT/$dest/.git" ]; then echo "skip $dest"; return; fi
  if git clone --depth 1 --quiet "https://github.com/$repo.git" "$ROOT/$dest" > "$ROOT/_logs/$(echo $dest | tr / _).log" 2>&1; then
    echo "OK $dest"; else echo "FAIL $dest"; fi
}
# --- colecciones principales
clone OpenScore/StringQuartets            openscore_quartets &
clone OpenScore/Lieder                    openscore_lieder &
clone iis-mctl/mctl-symphony-dataset      s3_symphonies &
clone DCMLab/ABC                          dcml_abc &
clone DCMLab/mozart_piano_sonatas         dcml_mozart_sonatas &
clone Wiilly07/Beethoven_motif            bps_motif &
wait
# --- KernScores (craigsapp + musedata + humdrum-tools)
for r in beethoven-piano-sonatas beethoven-string-quartets haydn-piano-sonatas mozart-piano-sonatas \
         scarlatti-keyboard-sonatas chopin-mazurkas chopin-preludes bach-370-chorales art-of-the-fugue \
         bach-musical-offering vivaldi-op6 scriabin joplin; do clone craigsapp/$r kern/$r & done
for r in humdrum-haydn-quartets humdrum-mozart-quartets humdrum-haydn-symphonies humdrum-bach-brandenburg \
         humdrum-corelli; do clone musedata/$r kern/$r & done
clone humdrum-tools/bach-wtc kern/bach-wtc &
wait
# --- DCML (subcorpus con notes.tsv + metadata.tsv)
for r in corelli couperin_concerts bach_solo bach_en_fr_suites handel_keyboard frescobaldi_fiori_musicali \
         sweelinck_keyboard peri_euridice monteverdi_madrigals pergolesi_stabat_mater cpe_bach_keyboard \
         jc_bach_sonatas wf_bach_sonatas kozeluh_sonatas pleyel_quartets scarlatti_sonatas \
         beethoven_piano_sonatas chopin_mazurkas mendelssohn_quartets schumann_kinderszenen \
         schumann_liederkreis schubert_winterreise liszt_pelerinage wagner_overtures grieg_lyric_pieces \
         tchaikovsky_seasons dvorak_silhouettes c_schumann_lieder mahler_kindertotenlieder \
         debussy_preludes debussy_suite_bergamasque medtner_tales rachmaninoff_piano ravel_piano \
         bartok_bagatelles poulenc_mouvements_perpetuels schulhoff_suite_dansante_en_jazz; do
  clone DCMLab/$r dcml/$r &
done
wait
# --- MuseData (CCARH) en Bitbucket: Beethoven completo (sinfonías 1-9 incl. op. 67, conciertos, cuartetos)
if [ -d "$ROOT/musedata_beethoven/.git" ]; then echo "skip musedata_beethoven"; else
  git clone --depth 1 --quiet https://bitbucket.org/musedata/beethoven.git "$ROOT/musedata_beethoven" && echo "OK musedata_beethoven" || echo "FAIL musedata_beethoven"
fi
echo "listo. Cherubini: ver corpus/raw/cherubini/README.md (codificación manual)."
