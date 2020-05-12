import os
import re
import json
import html
import requests
from requests.auth import HTTPBasicAuth
from jira import JIRA


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
        tags += (str("@" + tag).replace(" ", "-") + " ")

    return tags


def format_description_as_comment(description):
    formatted_desc = ""

    for line in description.split('\n'):
        formatted_desc += "\t# " + line

    return formatted_desc


def format_step(step):
    step = step.replace("GIVEN", "Given")
    step = step.replace("WHEN", "When")
    step = step.replace("THEN", "Then")
    step = step.replace("AND", "And")
    return step


def save_feature_file(feature_text, tags, scenario, steps, description, file_name):
    with open(save_directory + '/' + file_name + '.feature', 'w', encoding="utf-8") as file:
        file.write(format_tags_as_str(tags))
        file.write("\n")
        file.write("Feature: " + feature_text)
        if type(description) is str:
            file.write("\n")
            file.write(format_description_as_comment(description))
        file.write("\n\t")
        file.write("Scenario: " + scenario)
        file.write("\n")

        for step in steps:
            file.write("\t\t")
            file.write(format_step(step))
            file.write("\n")

        print('Wrote: ' + save_directory + '/' + file_name + '.feature')


def get_fix_versions(jira_obj):
    results = []

    for fix_version in jira_obj.fields.fixVersions:
        results.append(fix_version.name.replace(" ", "-"))

    return results


def get_issue_links(jira_obj):
    results = []

    for issue_link in jira_obj.fields.issuelinks:
        if (hasattr(issue_link, 'outwardIssue')):
            results.append(issue_link.outwardIssue.key)

    return results


# BEGIN MAIN
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

if not os.path.exists(save_directory):
    os.makedirs(save_directory)


jira = JIRA(jira_endpoint, basic_auth=(username, password))
zephyr_token = re.findall(r'"(.*?)"', re.search('zEncKeyVal = "\S+"', requests.get(jira_endpoint,
                                                                                   auth=HTTPBasicAuth(username, password), cookies=jira._session.cookies).text).group(0))[0]
jira._session.headers.update({str('AO-7DEABF').lower(): zephyr_token})

tests = jira.search_issues(jira_query, maxResults=999999)

for test in tests:
    steps = get_zephyr_test_steps(
        test.id, jira._session.cookies, jira._session.headers)
    if steps is None:
        print('Error: no steps found for Jira! ' + test.key)
    else:
        description = test.fields.description
        fix_versions = get_fix_versions(test)
        issue_links = get_issue_links(test)
        summary = test.fields.summary
        file_name = test.key
        tags = test.fields.labels + fix_versions + issue_links + [test.key]
        try:
            save_feature_file(summary, tags, summary,
                              steps, description, file_name)
        except:
            print('Error: Failed to write Feature file!')
            print('Filename: ' + file_name)
            print('Tags: ' + tags)
            print('Summary: ' + summary)
            print('Issue Links: ' + issue_links)
            print('Fix Versions: ' + fix_versions)
