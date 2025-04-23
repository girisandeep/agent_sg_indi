from django.shortcuts import render

# Create your views here.
# views.py
from django.views.generic import TemplateView
from django.http import StreamingHttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from chat.agent.chain_of_thought_runner import run_chain_of_thought_loop

# class ReactAppView(TemplateView):
#     template_name = "index.html"

@csrf_exempt
def chat_stream_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    try:
        body = json.loads(request.body)
        question = body["question"]
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

    def event_stream():
        for chunk in run_chain_of_thought_loop(question):
            yield f"data: {chunk}\n\n"

    return StreamingHttpResponse(event_stream(), content_type="text/event-stream")

