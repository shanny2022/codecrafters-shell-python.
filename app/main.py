def completer(text, state):
    """Autocomplete builtins and executables with longest-common-prefix support."""
    global last_prefix, tab_press_count

    builtins = ["echo", "exit"]
    matches = [b for b in builtins if b.startswith(text)]
    matches += get_executables_with_prefix(text)
    matches = sorted(set(matches))

    # If no matches
    if not matches:
        return None

    # If only one match, complete it fully
    if len(matches) == 1:
        tab_press_count = 0
        return matches[0] + " "

    # Multiple matches -> find common prefix
    common_prefix = longest_common_prefix(matches)

    if len(common_prefix) > len(text):
        # readline expects this to be the next part of completion
        tab_press_count = 0
        return common_prefix

    # Otherwise handle multiple TAB presses (bell / list)
    if last_prefix == text:
        tab_press_count += 1
    else:
        tab_press_count = 1
        last_prefix = text

    if tab_press_count == 1:
        sys.stdout.write("\a")
        sys.stdout.flush()
        return None
    elif tab_press_count == 2:
        sys.stdout.write("\n" + "  ".join(matches) + "\n")
        sys.stdout.write(f"$ {text}")
        sys.stdout.flush()
        return None

    return None
