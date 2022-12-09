import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from datetime import datetime
import boto3

session = boto3.session.Session()

# fill below
username = 'username'
icon_emoji = 'emoji'
slack_webhook_url = 'slack_webhook_url'
channel_name = 'slack_channel_name'


def slack_api_call(webhook_url, data):
    request = Request(
        webhook_url,
        data=json.dumps(data).encode(),
        headers={'Content-Type': 'application/json'}
    )
    response = urlopen(request)
    return response


class CloudWatchAlarmParser:
    def __init__(self, msg):
        try:
            self.msg = json.loads(msg["Message"])
        except:
            self.msg = msg
        self.timestamp_format = "%Y-%m-%dT%H:%M:%S.%f%z"
        self.trigger = self.msg["Trigger"]

        if self.msg['NewStateValue'] == "ALARM":
            self.color = "danger"
        elif self.msg['NewStateValue'] == "OK":
            self.color = "good"

    def __url(self):
        return ("https://console.aws.amazon.com/cloudwatch/home?"
                + urlencode({'region': session.region_name})
                + "#alarmsV2:alarm/"
                + self.msg["AlarmName"]
                )

    def slack_data(self):
        _message = {
            'text': '<!here|here>',  # add @here to message
            'attachments': [
                {
                    'title': ":aws: AWS CloudWatch Notification :alarm:",
                    'ts': datetime.strptime(
                        self.msg['StateChangeTime'],
                        self.timestamp_format
                    ).timestamp(),
                    'color': self.color,
                    'fields': [
                        {
                            "title": "Alarm Name",
                            "value": self.msg["AlarmName"],
                            "short": True
                        },
                        {
                            "title": "Alarm Description",
                            "value": self.msg["AlarmDescription"],
                            "short": False
                        },
                        {
                            "title": "Trigger",
                            "value": " ".join([
                                self.trigger["Statistic"],
                                self.trigger["MetricName"],
                                self.trigger["ComparisonOperator"],
                                str(self.trigger["Threshold"]),
                                "for",
                                str(self.trigger["EvaluationPeriods"]),
                                "period(s) of",
                                str(self.trigger["Period"]),
                                "seconds."
                            ]),
                            "short": False
                        },
                        {
                            'title': 'Old State',
                            'value': self.msg["OldStateValue"],
                            "short": True
                        },
                        {
                            'title': 'Current State',
                            'value': self.msg["NewStateValue"],
                            'short': True
                        },
                        {
                            'title': 'Link to Alarm',
                            'value': self.__url(),
                            'short': False
                        }
                    ]
                }
            ]
        }
        return _message


def lambda_handler(event, context):
    webhook_url = slack_webhook_url
    channel = channel_name
    send_data = {
        'channel': channel,
        'text': '새로운 알림이 있습니다.',
        'icon_emoji': icon_emoji,
        'username': username
    }

    response = slack_api_call(webhook_url, send_data)

    event_message = event['Records'][0]['Sns']['Message']
    try:
        message_text = json.loads(event_message)
        message = CloudWatchAlarmParser(message_text).slack_data()

        send_data["text"] = message["text"]
        send_data["attachments"] = message["attachments"]
    except:
        send_data["text"] = event_message

    response = slack_api_call(webhook_url, send_data)

    return {
        'statusCode': response.getcode(),
        'body': response.read().decode()
    }


if __name__ == "__main__":
    print(lambda_handler(None, None))
