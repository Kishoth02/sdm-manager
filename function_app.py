import azure.functions as func
import logging

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route="hello")
def hello_function(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('HTTP trigger function processed a request.')
    
    name = req.params.get('name', 'Kishoth')
    
    return func.HttpResponse(
        f"Hello {name}! Your Azure Function is working! 🎉",
        status_code=200
    )