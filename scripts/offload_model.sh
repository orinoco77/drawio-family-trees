#!/usr/bin/env bash
# Store/recall the user's OPTIONAL cheaper-model choice for chart grunt work.
#
# The skill never hardcodes a model: it must work for users on any provider.
# Instead the agent asks ONCE whether the user wants the mechanical chart
# steps (generate/verify/render) offloaded to a cheaper model they have
# configured, and records the answer here:
#
#   ~/.config/drawio-family-trees/offload-model
#
# States:
#   file missing        -> UNSET: ask the user once, then `set` their answer
#   file contains "off" -> user declined; run in-session, never ask again
#   anything else       -> model name usable with `hermes chat -m <name>`
#
# Usage:
#   offload_model.sh get           # print model name, "off", or "UNSET"
#   offload_model.sh set <value>   # store a model name, or "off"
#   offload_model.sh clear         # forget the choice (ask again next time)

set -euo pipefail

FILE="$HOME/.config/drawio-family-trees/offload-model"

case "${1:-get}" in
    get)
        if [[ -f "$FILE" ]]; then
            cat "$FILE"
        else
            echo "UNSET"
        fi
        ;;
    set)
        [[ $# -ge 2 && -n "$2" ]] || { echo "usage: offload_model.sh set <model|off>" >&2; exit 2; }
        mkdir -p "$(dirname "$FILE")"
        printf '%s\n' "$2" > "$FILE"
        echo "stored: $2"
        ;;
    clear)
        rm -f "$FILE"
        echo "cleared"
        ;;
    *)
        echo "usage: offload_model.sh [get|set <model|off>|clear]" >&2
        exit 2
        ;;
esac
