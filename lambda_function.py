# -*- coding: utf-8 -*-
# Import AWS SDK and set up IoT client
import uuid
import time
import boto3
import json

import logging

from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response
from ask_sdk_model.ui import SimpleCard

skill_name = "My Things"
friendly_name = "thermostat"
thing_count = 1
help_text = ("You can ask a thing for its status, or turn it on or off. " 
"You can say, ask " + friendly_name + ", or say, turn on " + friendly_name + ".")

friendly_name_slot_key = "MyFriendlyThingName"
on_off_slot_key = "OnOff"

sb = SkillBuilder()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# IoT client and client data
client = boto3.client('iot')
client_data = boto3.client('iot-data')

friendly_name_device_map = {friendly_name:"simulated-device-for-training"}

@sb.request_handler(can_handle_func=is_request_type("LaunchRequest"))
def launch_request_handler(handler_input):
    """Handler for Skill Launch."""
    # type: (HandlerInput) -> Response
    logger.info('lauch request received')
    user_id = handler_input.request_envelope.session.user.user_id
    logger.info('user_id = ' + user_id)

    speech = ("Welcome to my things. You have a total of " + str(thing_count) 
        + " things. They are: " + ", ".join(friendly_name_device_map.keys())) + "."

    handler_input.response_builder.speak(speech + " " + help_text).ask(help_text)
    return handler_input.response_builder.response

@sb.request_handler(can_handle_func=is_intent_name("WhatAreMyThingsIntent"))
def what_are_my_things_handler(handler_input):
    """Handler for what are my things intent"""
    return launch_request_handler(handler_input)


@sb.request_handler(can_handle_func=is_intent_name("TurnOnOffIntent"))
def turn_on_off_handler(handler_input):
    """Provided the friendly name of the thing, turn it on or off."""
    # type: (HandlerInput) -> Response
    slots = handler_input.request_envelope.request.intent.slots

    speech = "I can not find the name of the device you are asking for, please try again"
    reprompt = (help_text)

    if friendly_name_slot_key in slots:
        asked_friendly_name = slots[friendly_name_slot_key].value
        #handler_input.attributes_manager.session_attributes[
        #    friendly_name_slot_key] = asked_friendly_name
        # retrieve thing shadow
        askedOnOff = slots[on_off_slot_key].value
        logger.info('asked friendly thing name ' + asked_friendly_name)
        if asked_friendly_name in friendly_name_device_map.keys():
            # update shadow
            if askedOnOff == "on":
                desiredShadowJSON = '{"state":{"desired":{"led": "on"}}}'
                pubMessageJSON = '{"led": "on"}'
            else:
                desiredShadowJSON = '{"state":{"desired":{"led": "off"}}}'
                pubMessageJSON = '{"led": "off"}'
            client_data.update_thing_shadow(thingName=friendly_name_device_map[asked_friendly_name], payload=desiredShadowJSON)
            client_data.publish(
                    topic='iotdemo/topic/sub',
                    qos=0,
                    payload=pubMessageJSON
                )
            # check shadow after update and tell user. There is a delay for the reported state to reach the shadow 
            # therefore we are telling the desired state instead
            shadow = client_data.get_thing_shadow(thingName=friendly_name_device_map[asked_friendly_name])
            streamingBody = shadow["payload"]
            jsonState = json.loads(streamingBody.read())
            logger.info(jsonState)
            speech = ("turning {} ".format(asked_friendly_name)) + str(jsonState['state']['desired']['led'])
        else:
            logger.info('Unrecognised friendly name: ' + asked_friendly_name)
    else:
        logger.info('Not friendly name in slots.')

    handler_input.response_builder.speak(speech).ask(reprompt)
    return handler_input.response_builder.response


@sb.request_handler(can_handle_func=is_intent_name("AskByMyFriendlyThingNameIntent"))
def ask_by_my_friendly_thing_name_handler(handler_input):
    """Provided the friendly name of the thing, retrieve the current state 
    from the thing shadow and report to Alexa."""
    # type: (HandlerInput) -> Response
    slots = handler_input.request_envelope.request.intent.slots

    speech = "I can not find the device you are asking for, please try again"
    reprompt = (help_text)
    
    if friendly_name_slot_key in slots:
        asked_friendly_name = slots[friendly_name_slot_key].value
        logger.info('asked friendly thing name ' + asked_friendly_name)
        logger.info(friendly_name_device_map)
        if asked_friendly_name in friendly_name_device_map.keys():
            shadow = client_data.get_thing_shadow(thingName=friendly_name_device_map[asked_friendly_name])
            streamingBody = shadow["payload"]
            jsonState = json.loads(streamingBody.read())
            logger.info(jsonState)
            speech = ("The temperature of {} is ".format(asked_friendly_name)) + str(jsonState['state']['reported']['temperature']) + " degrees"
            reprompt = (help_text)
        else:
            logger.info("asked friendly name is not in the list")

    handler_input.response_builder.speak(speech).ask(reprompt)
    return handler_input.response_builder.response


@sb.request_handler(can_handle_func=is_intent_name("AMAZON.HelpIntent"))
def help_intent_handler(handler_input):
    """Handler for Help Intent."""
    # type: (HandlerInput) -> Response
    handler_input.response_builder.speak(help_text).ask(help_text)
    return handler_input.response_builder.response


@sb.request_handler(
    can_handle_func=lambda handler_input:
        is_intent_name("AMAZON.CancelIntent")(handler_input) or
        is_intent_name("AMAZON.StopIntent")(handler_input))
def cancel_and_stop_intent_handler(handler_input):
    """Single handler for Cancel and Stop Intent."""
    # type: (HandlerInput) -> Response
    speech_text = "Goodbye!"

    return handler_input.response_builder.speak(speech_text).response


@sb.request_handler(can_handle_func=is_request_type("SessionEndedRequest"))
def session_ended_request_handler(handler_input):
    """Handler for Session End."""
    # type: (HandlerInput) -> Response
    return handler_input.response_builder.response

@sb.request_handler(can_handle_func=is_intent_name("AMAZON.FallbackIntent"))
def fallback_handler(handler_input):
    """AMAZON.FallbackIntent is only available in en-US locale.
    This handler will not be triggered except in that locale,
    so it is safe to deploy on any locale.
    """
    # type: (HandlerInput) -> Response
    speech = (
        "The {} skill can't help you with that. " + help_text
        ).format(skill_name)
    reprompt = (help_text)
    handler_input.response_builder.speak(speech).ask(reprompt)
    return handler_input.response_builder.response


def convert_speech_to_text(ssml_speech):
    """convert ssml speech to text, by removing html tags."""
    # type: (str) -> str
    s = SSMLStripper()
    s.feed(ssml_speech)
    return s.get_data()


@sb.global_response_interceptor()
def add_card(handler_input, response):
    """Add a card by translating ssml text to card content."""
    # type: (HandlerInput, Response) -> None
    response.card = SimpleCard(
        title=skill_name,
        content=convert_speech_to_text(response.output_speech.ssml))


@sb.global_response_interceptor()
def log_response(handler_input, response):
    """Log response from alexa service."""
    # type: (HandlerInput, Response) -> None
    print("Alexa Response: {}\n".format(response))


@sb.global_request_interceptor()
def log_request(handler_input):
    """Log request to alexa service."""
    # type: (HandlerInput) -> None
    print("Alexa Request: {}\n".format(handler_input.request_envelope.request))


@sb.exception_handler(can_handle_func=lambda i, e: True)
def all_exception_handler(handler_input, exception):
    """Catch all exception handler, log exception and
    respond with custom message.
    """
    # type: (HandlerInput, Exception) -> None
    print("Encountered following exception: {}".format(exception))

    speech = "Sorry, there was some problem. Please try again!!"
    handler_input.response_builder.speak(speech).ask(speech)

    return handler_input.response_builder.response


######## Convert SSML to Card text ############
# This is for automatic conversion of ssml to text content on simple card
# You can create your own simple cards for each response, if this is not
# what you want to use.

from six import PY2
try:
    from HTMLParser import HTMLParser
except ImportError:
    from html.parser import HTMLParser


class SSMLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.full_str_list = []
        if not PY2:
            self.strict = False
            self.convert_charrefs = True

    def handle_data(self, d):
        self.full_str_list.append(d)

    def get_data(self):
        return ''.join(self.full_str_list)

################################################


# Handler to be provided in lambda console.
lambda_handler = sb.lambda_handler()
