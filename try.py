import inspect
import signal

signals = {
    name: sig.value
    for name, sig in inspect.getmembers(signal, lambda x: isinstance(x, signal.Signals))
    if not name.startswith("SIG_")  # skip SIG_DFL, SIG_IGN, etc.
}

# Sort by number then name
for name, number in sorted(signals.items(), key=lambda kv: (kv[1], kv[0])):
    print(f"{number:2}  {name}")
