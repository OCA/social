* Better live-updating of an edited message in the thread, right now only
  'body' parameter is updated.
* For the body parameter, call processBody to correctly handle emoji.
* Live-update edited message through all threads, using the message bus.
