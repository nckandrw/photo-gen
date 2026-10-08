#!/bin/zsh
# Q-Q feasibility smoke (PROTOCOL.md §4): q8 on the G0 source E05 (not a G2 item; not evidence). Marker QQ_SMOKE_DONE.
main() {
cd ~/Dev/photo-gen
echo "QQ_SMOKE_START $(date) git=$(git rev-parse HEAD)"
zsh research/qwen/run_edit.sh QQSMOKE-512-E05-q8 qq:q8 /Users/nckandrw/Dev/photo-gen/data/inputs/8f55b71b446a702453dac9defa382e97d762ad94ac224940de46f11e21b39f4a.png 512 42 'Change the background to a sunset beach' 40
sleep 20
zsh research/qwen/run_edit.sh QQSMOKE-1024-E05-q8-3steps qq:q8 /Users/nckandrw/Dev/photo-gen/data/inputs/8f55b71b446a702453dac9defa382e97d762ad94ac224940de46f11e21b39f4a.png 1024 42 'Change the background to a sunset beach' 3
echo "QQ_SMOKE_DONE $(date)"
}
main "$@"; exit $?
