# Handles POST /guestbook -- adds item to guestbook 
#


from flask import request
from flask import current_app
def fib(n):
    if n == 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fib(n-1)+fib(n-2)


def main():
    # Read the item from POST params, add it to redis, and redirect
    # back to the list
    current_app.logger.info("HTTP Request")
    n = int(request.get_data()) 
    result = []
    for i in range(n):
       result.append(str(fib(i)))
       joined = ','.join(result)
    #return result
    #print (', '.join(result))
    return('The join output is: ' + joined)


