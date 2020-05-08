from requests.auth import HTTPBasicAuth
from jira import JIRA
import json
import requests
import re
import os
import pathlib
import textwrap
import html

username = os.environ.get("JIRA_USERNAME")
password = os.environ.get("JIRA_PASSWORD")
jira_endpoint = os.environ.get("JIRA_URL")
jira_query = os.environ.get("JIRA_QUERY")

env_var_errors = False
env_var_messages = []

if not username:
    env_var_messages.append('JIRA_USERNAME')
    env_var_errors = True

if not password:
    env_var_messages.append('JIRA_PASSWORD')
    env_var_errors = True

if not jira_endpoint:
    env_var_messages.append('JIRA_URL')
    env_var_errors = True

if not jira_query:
    env_var_messages.append('JIRA_QUERY')
    env_var_errors = True

if env_var_errors:
    print("Error, you need to set these env variables!")
    for message in env_var_messages:
        print(message)
    exit(1)

save_directory = str(os.path.dirname(os.path.dirname(
    os.path.realpath(__file__)) + '/features/')).replace('\\', '/')
1
if not os.path.exists(save_directory):
    os.makedirs(save_directory)

# Begin Helper Functions
def parse_zephyr_test_steps(json_response):
    if len(json_response['stepBeanCollection']) >= 1:
        steps = []
        clean = re.compile('<.*?>')
        for step in json_response['stepBeanCollection']:
            step_str = re.sub(clean, '', step['htmlStep'])
            step_str = html.unescape(step_str)
            steps.append(step_str)
        return steps


def get_zephyr_test_steps(p_test_id, p_cookies, p_headers):
    response = requests.get(jira_endpoint + "/rest/zephyr/latest/teststep/" +
                            p_test_id, cookies=p_cookies, headers=p_headers)
    if response.ok:
        steps = parse_zephyr_test_steps(json.loads(response.text))
        if steps:
            return steps
    return None


def format_tags_as_str(p_tags):
    tags = ""

    for tag in p_tags:
        tags += "@" + tag + " "

    return tags


def format_steps_as_str(p_steps):
    steps = ""

    for step in p_steps:
        steps += step + "\n"

    return steps


def save_feature_file(feature_text, tags, scenario, steps, file_name):
    with open(save_directory + '/' + file_name + '.feature', 'w') as file:
        file.writelines(textwrap.dedent(f"""\
Feature: {feature_text}
    {format_tags_as_str(tags)}
    Scenario: {scenario}
    {format_steps_as_str(steps)}
                        """))

        print('Wrote: ' + save_directory + '/' + file_name + '.feature')
# End Helper Functions


jira = JIRA(jira_endpoint, basic_auth=(username, password))
zephyr_token = re.findall(r'"(.*?)"', re.search('zEncKeyVal = "\S+"', requests.get(jira_endpoint,
                                                                                   auth=HTTPBasicAuth(username, password), cookies=jira._session.cookies).text).group(0))[0]
jira._session.headers.update({str('AO-7DEABF').lower(): zephyr_token})

tests = jira.search_issues(jira_query)

for test in tests:
    steps = get_zephyr_test_steps(
        test.id, jira._session.cookies, jira._session.headers)
    if steps is None:
        print('Error: no steps found for Jira! ' + test.key)
    else:
        summary = test.fields.summary
        file_name = test.key
        labels = test.fields.labels

        save_feature_file(file_name, labels, summary, steps, file_name)
