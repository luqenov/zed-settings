#!/usr/bin/env bash

check_init() {
    local project="$1"
    shift
    CHECK_VERBOSE=false
    CHECK_PLAIN=false
    for option in "$@"; do
        case "$option" in
            --verbose|-v) CHECK_VERBOSE=true ;;
            --plain) CHECK_PLAIN=true ;;
            --help|-h)
                printf 'Usage: %s [--verbose] [--plain]\n\n' "$0"
                printf 'Show concise check results. Details appear automatically on failure.\n'
                printf '  --verbose  Show successful command output and individual tests too\n'
                printf '  --plain    Disable terminal animation and colors\n'
                exit 0 ;;
            *) printf 'Unknown option: %s\n' "$option" >&2; exit 2 ;;
        esac
    done
    CHECK_ANIMATE=false
    CHECK_GREEN='' CHECK_RED='' CHECK_RESET=''
    if [[ -t 1 && ${TERM:-dumb} != dumb && -z ${CI:-} && $CHECK_PLAIN == false ]]; then
        CHECK_ANIMATE=true
        if [[ ! ${NO_COLOR+x} ]]; then
            CHECK_GREEN=$'\033[32m' CHECK_RED=$'\033[31m' CHECK_RESET=$'\033[0m'
        fi
    fi
    export PYTHONDONTWRITEBYTECODE=1
    export CHECK_TEST_FLAG=-q
    if [[ $CHECK_VERBOSE == true ]]; then export CHECK_TEST_FLAG=-v; fi
    CHECK_STEPS=0 CHECK_TESTS=0 CHECK_SKIPPED_TESTS=0 CHECK_SKIPPED_STEPS=0
    CHECK_STARTED=$SECONDS
    CHECK_CHILD_PID=''
    CHECK_LOG_DIR="$(mktemp -d "${TMPDIR:-/tmp}/repo-checks.XXXXXXXX")"
    trap check_cleanup EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
    printf '\nChecking %s\n\n' "$project"
}

check_cleanup() {
    if [[ -n ${CHECK_CHILD_PID:-} ]]; then
        kill -TERM "$CHECK_CHILD_PID" 2>/dev/null || :
        wait "$CHECK_CHILD_PID" 2>/dev/null || :
    fi
    if [[ -n ${CHECK_LOG_DIR:-} ]]; then rm -rf -- "$CHECK_LOG_DIR"; fi
}

check_dependencies() {
    local dependency
    for dependency in "$@"; do
        command -v "$dependency" >/dev/null || { printf 'Missing dependency: %s\n' "$dependency" >&2; return 1; }
    done
}

check_record_tests() {
    local line count=0 skipped=0
    while IFS= read -r line || [[ -n $line ]]; do
        if [[ $line =~ ^Ran[[:space:]]+([0-9]+)[[:space:]]+tests? ]]; then
            count="${BASH_REMATCH[1]}"
        elif [[ $line =~ ^#[[:space:]]tests[[:space:]]([0-9]+) ]]; then
            count="${BASH_REMATCH[1]}"
        fi
        if [[ $line =~ skipped=([0-9]+) ]]; then
            skipped="${BASH_REMATCH[1]}"
        elif [[ $line =~ ^#[[:space:]]skipped[[:space:]]([0-9]+) ]]; then
            skipped="${BASH_REMATCH[1]}"
        fi
    done < "$1"
    CHECK_TESTS=$((CHECK_TESTS + count))
    CHECK_SKIPPED_TESTS=$((CHECK_SKIPPED_TESTS + skipped))
}

check_step() {
    local label="$1"
    shift
    local log="$CHECK_LOG_DIR/step.log" started=$SECONDS result=0 frame=0
    local frames=('|' '/' '-' "\\")
    if [[ $CHECK_ANIMATE == false ]]; then printf '  %s ... ' "$label"; fi
    # NOTE: explicit stdin forwarding preserves validation scripts supplied by heredoc.
    "$@" <&0 > "$log" 2>&1 &
    CHECK_CHILD_PID=$!
    if [[ $CHECK_ANIMATE == true ]]; then
        while kill -0 "$CHECK_CHILD_PID" 2>/dev/null; do
            printf '\r\033[2K  %s  %s' "${frames[frame % ${#frames[@]}]}" "$label"
            frame=$((frame + 1))
            sleep 0.1
        done
    fi
    if wait "$CHECK_CHILD_PID"; then :; else result=$?; fi
    CHECK_CHILD_PID=''
    if [[ $CHECK_ANIMATE == true ]]; then printf '\r\033[2K'; fi
    if (( result != 0 )); then
        if [[ $CHECK_ANIMATE == true ]]; then
            printf '  %sFAIL%s  %s\n' "$CHECK_RED" "$CHECK_RESET" "$label"
        else
            printf 'FAIL\n'
        fi
        printf '\n'
        cat "$log"
        printf '\nStopped at: %s (exit %s).\n' "$label" "$result" >&2
        return "$result"
    fi
    CHECK_STEPS=$((CHECK_STEPS + 1))
    check_record_tests "$log"
    if [[ $CHECK_ANIMATE == true ]]; then
        printf '  %sOK%s  %s (%ss)\n' "$CHECK_GREEN" "$CHECK_RESET" "$label" "$((SECONDS - started))"
    else
        printf 'OK\n'
    fi
    if [[ $CHECK_VERBOSE == true && -s $log ]]; then
        printf '\n'
        cat "$log"
        printf '\n'
    fi
}

check_skip() {
    CHECK_SKIPPED_STEPS=$((CHECK_SKIPPED_STEPS + 1))
    printf '  %s ... SKIPPED (%s)\n' "$1" "$2"
}

check_finish() {
    local checks_label=checks tests_label=tests skipped_label=checks
    if (( CHECK_STEPS == 1 )); then checks_label=check; fi
    if (( CHECK_TESTS == 1 )); then tests_label='test'; fi
    printf '\nPassed: %s %s' "$CHECK_STEPS" "$checks_label"
    if (( CHECK_TESTS > 0 )); then printf ', %s %s' "$CHECK_TESTS" "$tests_label"; fi
    printf ' (%ss).\n' "$((SECONDS - CHECK_STARTED))"
    if (( CHECK_SKIPPED_STEPS + CHECK_SKIPPED_TESTS > 0 )); then
        tests_label=tests
        if (( CHECK_SKIPPED_TESTS == 1 )); then tests_label='test'; fi
        if (( CHECK_SKIPPED_STEPS == 1 )); then skipped_label=check; fi
        printf 'Skipped: %s optional %s, %s %s.\n' "$CHECK_SKIPPED_STEPS" "$skipped_label" "$CHECK_SKIPPED_TESTS" "$tests_label"
    fi
}
