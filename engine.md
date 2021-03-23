# acquisition engine

## micro-manager (mmstudio)

1. AcqControlDlg.runAcquisition();
   1. applySettingsFromGUI();
      1. SequenceSettings.Builder();  -> build events from gui
      2. acqEng_.setSequenceSettings(ssb.build())
   2. return acqEng_.acquire();
      1. AcquisitionWrapperEngine.runAcquisition();
         (not immediately clear how we get to clojure engine: acquisitionEngine2010_?)
      2. optimize and execute sequence...

# pycro-manager

1. generate list of events (e.g. multi_d_acquisition_events) -> build events from function
2. put them in the event_queu
3. acqj.api.Acquisition.submitEventIterator(elist)
   1. processAcquisitionEvent (merge/optimize ... similar to acqEngine->generate-acq-sequence)
   2. executeAcquisitionEvent (execute event with hooks ... similar to acqEngine->execute)

# napari-micromanager

1. generate multiD experiment from gui with MultiDExperiment dataframe
   1. MultiDExperiment object iterates Frame objects
   2. similar to SequenceSettings.Builder() and/or creation of list of pycro-manager events
2. internal python acqEngine drives CMMCore
   1. similar to pycro-submitEventIterator, similar to clojure run-acquisition



## clojure

def run-acquisition(settings, out-queue)
    acq-seq = generate-acq-sequence(settings)
    for seq in acq-seq:
        execute(seq, out-queue, settings)

def execute(event, out-queue, settings)
    set xy position
    set channel properties
    set exposure
    recall-z-reference
    wait...
    autofocus
    set Z
    for runnable in event.runnables:
        run(runnable)
    aquire image

## AcqEngJ

1. submitEventIterator (takes list of events)
2. processAcquisitionEvent (merge/optimize ... similar to acqEngine->generate-acq-sequence)
3. executeAcquisitionEvent (execute event with hooks ... similar to acqEngine->execute)

# considerations

- changing events
- pausing
- non-acquisition events
