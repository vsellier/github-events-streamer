

class QueryType(Enum):
    GetLastEvent = 0
    GetEventsPage = 1

class ResponseStatus(Enum):
    OK = 0
    KO = 1

class ApiResponse():
  def __init__(self, *args, **kwargs):
    return super().__init__(*args, **kwargs)
