import sys
sys.path.insert(0, 'package/')

import json
import requests
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)



def sendDiscordNotification(msg, webhook):

    discordUserSender = os.getenv("USERNAME_SENDER")
    discordAvatarUrl = os.getenv("USERNAME_AVATAR_URL")
    discordMessage = msg

    discordNotificationJsonPayload = {
        "username": discordUserSender,
        "avatar_url": discordAvatarUrl,
        "content": discordMessage,
        "embeds": '',
        "attachments": []
    }

    headers = {
        'content-type': 'application/json'
    }


    print(f'SEND Request >>>>> sendDiscordNotification...')

    try:

        response = requests.post(webhook, data=json.dumps(discordNotificationJsonPayload), headers=headers)

        return {
            'status_code': response.status_code,
            'content': response.content
        }

    except Exception as erro:
        print(f'ERROR to SEND Request >>>>> sendDiscordNotification {erro}')



def transformDictToText(dictObject):
    messageBody = []

    for (key, value) in dictObject.items():
        messageBody.append(f"**{key}**: {value}")

    response = f"""

{'#####> '.join(messageBody)}

""".replace("#####", "\n")

    return response



def parseObjectNotification(dictObject, service=None, shortMessage=False):

    originNotificationDict = dictObject

    newNotificationDict = None

    customizedServicesAvailable = [
        "EC2",
        "RDS",
        "Lambda"
    ]


    print(f'START >>>>> parseObjectNotification [originNotificationDict]: {originNotificationDict}')


    if service is not None:

        if service in customizedServicesAvailable:

            if not shortMessage:

                newNotificationDict = {
                    "Alarm": originNotificationDict["AlarmName"],
                    "Description": originNotificationDict["AlarmDescription"],
                    "AWSAccountId": originNotificationDict["AWSAccountId"],
                    "Updated Timestamp": originNotificationDict["AlarmConfigurationUpdatedTimestamp"],
                    "Previous Status": originNotificationDict["OldStateValue"],
                    "New Status": originNotificationDict["NewStateValue"],
                    "Reason": originNotificationDict["NewStateReason"],
                    "State ChangeTime": originNotificationDict["StateChangeTime"],
                    "Region": originNotificationDict["Region"],
                    "Alarm ARN": originNotificationDict["AlarmArn"],
                    "Trigger MetricName": originNotificationDict["Trigger"]["MetricName"],
                    "Trigger ComparisonOperator": originNotificationDict["Trigger"]["ComparisonOperator"],
                    "Trigger Threshold": str(originNotificationDict["Trigger"]["Threshold"]),
                    "Trigger NameSpace": originNotificationDict["Trigger"]["Namespace"],
                    originNotificationDict["Trigger"]["Dimensions"][0]["name"] if len(originNotificationDict["Trigger"]["Dimensions"]) > 0 else "Trigger Dimensions": originNotificationDict["Trigger"]["Dimensions"][0]["value"] if len(originNotificationDict["Trigger"]["Dimensions"]) > 0 else None
                }


            else:

                newNotificationDict = {
                    "Alarm": originNotificationDict["AlarmName"],
                    "Description": originNotificationDict["AlarmDescription"],
                    "Trigger MetricName": originNotificationDict["Trigger"]["MetricName"],
                    "Trigger Threshold": str(originNotificationDict["Trigger"]["Threshold"]),
                    "Status": originNotificationDict["NewStateValue"],
                    originNotificationDict["Trigger"]["Dimensions"][0]["name"] if len(originNotificationDict["Trigger"]["Dimensions"]) > 0 else "Trigger Dimensions": originNotificationDict["Trigger"]["Dimensions"][0]["value"] if len(originNotificationDict["Trigger"]["Dimensions"]) > 0 else None
                }


    else: # if not service

        if originNotificationDict.get("Records", None) is not None:

            if originNotificationDict["Records"][0]["eventSource"] == 'aws:s3':
                newNotificationDict = {
                    "Event Source": originNotificationDict["Records"][0]["eventSource"],
                    "Region": originNotificationDict["Records"][0]["awsRegion"],
                    "Event Time": originNotificationDict["Records"][0]["eventTime"],
                    "User Identity": originNotificationDict["Records"][0]["userIdentity"]["principalId"],
                    "Source IP Address": originNotificationDict["Records"][0]["requestParameters"]["sourceIPAddress"],
                    "S3 Bucket Name": originNotificationDict["Records"][0]["s3"]["bucket"]["name"],
                    "Bucket Owner Identity": originNotificationDict["Records"][0]["s3"]["bucket"]["ownerIdentity"]["principalId"],
                    "Bucket ARN": originNotificationDict["Records"][0]["s3"]["bucket"]["arn"],
                    "Event Name": originNotificationDict["Records"][0]["eventName"],
                    "Object KEY": originNotificationDict["Records"][0]["s3"]["object"]["key"],
                    "Object SIZE": str(originNotificationDict["Records"][0]["s3"]["object"]["size"])
                }


    print(f'AFTER >>>>> parseObjectNotification RETURN [newNotificationDict]: {newNotificationDict}')


    if newNotificationDict is not None:
        try:
            NotificationString = transformDictToText(newNotificationDict)
            return NotificationString

        except Exception as erro:
            print(erro)

    else:
        print(f'IS NOT [newNotificationDict] >>>>> RETURN [json.dumps(originNotificationDict, indent=4)]: {json.dumps(originNotificationDict, indent=4)}')
        return f"""
```
{json.dumps(originNotificationDict, indent=4)}
```
"""


def handler(event, context):

    webhookUrl = os.getenv("WEBHOOK_URL")
    shortMessage = os.getenv("SHORT_MSG", False)

    parsedMessage = []
    generalMessage = ""


    for record in event.get('Records', []):

        snsMessage = json.loads(record['Sns']['Message'])

        isAlarmTrigger = snsMessage.get('Trigger', None)


        if isAlarmTrigger:

            namespaceAlarm = isAlarmTrigger.get('Namespace', 0)

            if namespaceAlarm == 'AWS/Lambda':
                print(f'PARSE MESSAGE to >>>>> {namespaceAlarm}')
                parsedMessage = parseObjectNotification(snsMessage, 'Lambda', shortMessage)


            elif namespaceAlarm == 'AWS/EC2' or namespaceAlarm == 'CWAgent':
                print(f'PARSE MESSAGE to >>>>> {namespaceAlarm}')
                parsedMessage = parseObjectNotification(snsMessage, 'EC2', shortMessage)


            elif namespaceAlarm == 'AWS/RDS':
                print(f'PARSE MESSAGE to >>>>> {namespaceAlarm}')
                parsedMessage = parseObjectNotification(snsMessage, 'RDS', shortMessage)



        if not parsedMessage:

            generalMessage = parseObjectNotification(snsMessage)

            print(f'SEND ALARM [generalMessage] >>>>> {generalMessage}')
            sendDiscordNotification(generalMessage, webhookUrl)

        
        else:

            print(f'SEND CUSTOM ALARM [parsedMessage] >>>>> {parsedMessage}')
            sendDiscordNotification(parsedMessage, webhookUrl)
