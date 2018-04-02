from rest_framework import status
from rest_framework.response import Response

from boocoin.util.views import APIView


def process_form(serializer_class, request, data=None, return_response=True,
                 empty_response=False, **kwargs):
    """
    Initializes a serializer with the request and request's data, verifies
    it is valid, and calls save() on the serializer. Returns a response of the
    serializer's finalized data.
    """
    # Source the data from the request unless it was explicitly provided
    data = data or request.data

    # Create the context for the serializer
    context = {'request': request}

    # Add additional data if it was provided
    if kwargs:
        data.update(kwargs)

    # Initialize, validate and save the serializer
    serializer = serializer_class(data=data, context={'request': request})
    serializer.is_valid(raise_exception=True)
    serializer.save()

    # Return the serializer if we don't need to return a response
    if not return_response:
        return serializer

    # Return the appropriate response
    try:
        return Response(serializer.data if not empty_response else None)
    except ValueError:
        return Response(status=status.HTTP_204_NO_CONTENT)


class FormView(APIView):
    """
    A convenience class for processing a form (serializer) with POST data.
    Simply define the serializer_class to use it.
    """
    serializer_class = None
    empty_response = False

    def post(self, request):
        return process_form(self.serializer_class, request=request,
                            empty_response=self.empty_response)
