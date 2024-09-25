import useq

seq = useq.MDASequence(time_plan=useq.TIntervalDuration(interval=0, duration=3))

for n, _e in enumerate(seq):
    print("hi", n)
    if n > 10:
        break
