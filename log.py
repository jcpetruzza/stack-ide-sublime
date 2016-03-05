try:
    import sublime
except ImportError:
    from test.stubs import sublime

class Log:
  """
  Logging facilities
  """

  verbosity = None

  VERB_NONE    = 0
  VERB_ERROR   = 1
  VERB_WARNING = 2
  VERB_NORMAL  = 3
  VERB_DEBUG   = 4

  @classmethod
  def reset(cls):
      cls.verbosity = None

  @classmethod
  def error(cls,*msg):
      cls._record(cls.VERB_ERROR, *msg)

  @classmethod
  def warning(cls,*msg):
      cls._record(cls.VERB_WARNING, *msg)

  @classmethod
  def normal(cls,*msg):
      cls._record(cls.VERB_NORMAL, *msg)

  @classmethod
  def debug(cls,*msg):
      cls._record(cls.VERB_DEBUG, *msg)

  @classmethod
  def _record(cls, verb, *msg):
      if not cls.verbosity:
          cls._set_verbosity("none")

      if verb <= cls.verbosity:
          for line in ''.join(map(lambda x: str(x), msg)).split('\n'):
              print('[SublimeStackIDE]['+cls._show_verbosity(verb)+']:',*msg)

          if verb == cls.VERB_ERROR:
              sublime.status_message('There were errors, check the console cls')
          elif verb == cls.VERB_WARNING:
              sublime.status_message('There were warnings, check the console cls')

  @classmethod
  def _set_verbosity(cls, input):

      verb = input.lower()

      if verb == "none":
          cls.verbosity = cls.VERB_NONE
      elif verb == "error":
          cls.verbosity = cls.VERB_ERROR
      elif verb == "warning":
          cls.verbosity = cls.VERB_WARNING
      elif verb == "normal":
          cls.verbosity = cls.VERB_NORMAL
      elif verb == "debug":
          cls.verbosity = cls.VERB_DEBUG
      else:
          cls.verbosity = cls.VERB_WARNING
          cls.warning("Invalid verbosity: '" + str(verb) + "'")

  @classmethod
  def _show_verbosity(cls,verb):
      return ["?!","ERROR","WARN","NORM","DEBUG"][verb]
