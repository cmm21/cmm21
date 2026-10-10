import datetime
from dateutil import relativedelta
import requests
import os
from lxml import etree
import time
import hashlib

# Fine-grained personal access token with All Repositories access:
# Account permissions: read:Followers, read:Starring, read:Watching
# Repository permissions: read:Commit statuses, read:Contents, read:Issues, read:Metadata, read:Pull Requests
# Issues and pull requests permissions not needed at the moment, but may be used in the future
HEADERS = {'authorization': 'token '+ os.environ['ACCESS_TOKEN']}
USER_NAME = 'cmm21'
QUERY_COUNT = {'user_getter': 0, 'follower_getter': 0, 'graph_repos_stars': 0, 'recursive_loc': 0, 'graph_commits': 0, 'loc_query': 0}


def daily_readme(birthday):
    """
    Returns the length of time since I was born
    e.g. 'XX years, XX months, XX days'
    """
    diff = relativedelta.relativedelta(datetime.datetime.today(), birthday)
    return '{} {}, {} {}, {} {}{}'.format(
        diff.years, 'year' + format_plural(diff.years), 
        diff.months, 'month' + format_plural(diff.months), 
        diff.days, 'day' + format_plural(diff.days),
        ' 🎂' if (diff.months == 0 and diff.days == 0) else '')


def format_plural(unit):
    """
    Returns a properly formatted number
    e.g.
    'day' + format_plural(diff.days) == 5
    >>> '5 days'
    'day' + format_plural(diff.days) == 1
    >>> '1 day'
    """
    return 's' if unit != 1 else ''


def simple_request(func_name, query, variables):
    """
    Returns a request, or raises an Exception if the response does not succeed.
    """
    request = requests.post('https://api.github.com/graphql', json={'query': query, 'variables':variables}, headers=HEADERS)
    if request.status_code == 200:
        return request
    raise Exception(func_name, ' has failed with a', request.status_code, request.text, QUERY_COUNT)


def graph_commits(start_date, end_date):
    """
    Uses GitHub's GraphQL v4 API to return my total commit count
    """
    query_count('graph_commits')
    query = '''
    query($start_date: DateTime!, $end_date: DateTime!, $login: String!) {
        user(login: $login) {
            contributionsCollection(from: $start_date, to: $end_date) {
                contributionCalendar {
                    totalContributions
                }
            }
        }
    }'''
    variables = {'start_date': start_date,'end_date': end_date, 'login': USER_NAME}
    request = simple_request(graph_commits.__name__, query, variables)
    return int(request.json()['data']['user']['contributionsCollection']['contributionCalendar']['totalContributions'])


def graph_repos_stars(count_type, owner_affiliation, cursor=None, add_loc=0, del_loc=0):
    """
    Uses GitHub's GraphQL v4 API to return my total repository, star, or lines of code count.
    """
    query_count('graph_repos_stars')
    query = '''
    query ($owner_affiliation: [RepositoryAffiliation], $login: String!, $cursor: String) {
        user(login: $login) {
            repositories(first: 100, after: $cursor, ownerAffiliations: $owner_affiliation) {
                totalCount
                edges {
                    node {
                        ... on Repository {
                            nameWithOwner
                            stargazers {
                                totalCount
                            }
                        }
                    }
                }
                pageInfo {
                    endCursor
                    hasNextPage
                }
            }
        }
    }'''
    variables = {'owner_affiliation': owner_affiliation, 'login': USER_NAME, 'cursor': cursor}
    request = simple_request(graph_repos_stars.__name__, query, variables)
    if request.status_code == 200:
        if count_type == 'repos':
            return request.json()['data']['user']['repositories']['totalCount']
        elif count_type == 'stars':
            return stars_counter(request.json()['data']['user']['repositories']['edges'])


def get_yearly_contributions(start_date, end_date):
    query_count('graph_commits')
    query = '''
    query($start_date: DateTime!, $end_date: DateTime!, $login: String!) {
        user(login: $login) {
            contributionsCollection(from: $start_date, to: $end_date) {
                totalCommitContributions
                totalPullRequestContributions
                restrictedContributionsCount
            }
        }
    }'''
    variables = {'start_date': start_date, 'end_date': end_date, 'login': USER_NAME}
    request = simple_request('get_yearly_contributions', query, variables)
    if request.status_code == 200:
        data = request.json()['data']['user']['contributionsCollection']
        return data['totalCommitContributions'] + data.get('restrictedContributionsCount', 0), data['totalPullRequestContributions']
    return 0, 0

def get_total_prs():
    query = '''
    query {
      search(query: "author:cmm21 type:pr", type: ISSUE, first: 1) {
        issueCount
      }
    }
    '''
    request = simple_request('get_total_prs', query, {})
    if request.status_code == 200:
        return request.json()['data']['search']['issueCount']
    return 0

def get_total_reviews():
    query = '''
    query {
      search(query: "reviewed-by:cmm21 type:pr", type: ISSUE, first: 1) {
        issueCount
      }
    }
    '''
    request = simple_request('get_total_reviews', query, {})
    if request.status_code == 200:
        return request.json()['data']['search']['issueCount']
    return 0

def get_total_contributions(acc_datetime):
    total_commits = 543 # Archived commits
    now = datetime.datetime.now(datetime.UTC)
    current_start = acc_datetime.replace(tzinfo=datetime.timezone.utc)
    
    while current_start < now:
        current_end = current_start + relativedelta.relativedelta(years=1)
        if current_end > now:
            current_end = now
            
        commits, _ = get_yearly_contributions(current_start.isoformat().replace('+00:00', 'Z'), current_end.isoformat().replace('+00:00', 'Z'))
        total_commits += commits
        
        current_start = current_end
        
    return total_commits, get_total_prs(), get_total_reviews()



def user_getter(username):
    """
    Returns the account ID and creation time of the user
    """
    query_count('user_getter')
    query = '''
    query($login: String!){
        user(login: $login) {
            id
            createdAt
        }
    }'''
    variables = {'login': username}
    request = simple_request(user_getter.__name__, query, variables)
    return {'id': request.json()['data']['user']['id']}, request.json()['data']['user']['createdAt']

def follower_getter(username):
    """
    Returns the number of followers of the user
    """
    query_count('follower_getter')
    query = '''
    query($login: String!){
        user(login: $login) {
            followers {
                totalCount
            }
        }
    }'''
    request = simple_request(follower_getter.__name__, query, {'login': username})
    return int(request.json()['data']['user']['followers']['totalCount'])


def query_count(funct_id):
    """
    Counts how many times the GitHub GraphQL API is called
    """
    global QUERY_COUNT
    QUERY_COUNT[funct_id] += 1


def perf_counter(funct, *args):
    """
    Calculates the time it takes for a function to run
    Returns the function result and the time differential
    """
    start = time.perf_counter()
    funct_return = funct(*args)
    return funct_return, time.perf_counter() - start


def formatter(query_type, difference, funct_return=False, whitespace=0):
    """
    Prints a formatted time differential
    Returns formatted result if whitespace is specified, otherwise returns raw result
    """
    print('{:<23}'.format('   ' + query_type + ':'), sep='', end='')
    print('{:>12}'.format('%.4f' % difference + ' s ')) if difference > 1 else print('{:>12}'.format('%.4f' % (difference * 1000) + ' ms'))
    if whitespace:
        return f"{'{:,}'.format(funct_return): <{whitespace}}"
    return funct_return



def update_xp_bar(root, acc_datetime):
    now = datetime.datetime.now(datetime.UTC)
    acc_utc = acc_datetime.replace(tzinfo=datetime.timezone.utc)
    diff = relativedelta.relativedelta(now, acc_utc)
    
    days_passed = (diff.months * 30.44) + diff.days
    percent = min(1.0, days_passed / 365.25)
    bar_width = int(500 * percent)
    
    rect = root.find(f".//*[@id='xp_bar_fill']")
    if rect is not None:
        rect.attrib['width'] = str(bar_width)
        
    level = diff.years
    level_text = root.find(f".//*[@id='level_data']")
    if level_text is not None:
        level_text.text = f"Level {level} Software Engineer"
def svg_overwrite(filename, age_data, commit_data, total_prs, total_reviews, acc_datetime=None):
    try:
        tree = etree.parse(filename)
    except OSError:
        return
    root = tree.getroot()
    justify_format(root, 'commit_data', commit_data, 37)
    justify_format(root, 'pr_data', total_prs, 42)
    justify_format(root, 'age_data', age_data, 36)
    if acc_datetime:
        update_xp_bar(root, acc_datetime)
    justify_format(root, 'review_data', total_reviews, 28)
    tree.write(filename, encoding='utf-8', xml_declaration=True)

def justify_format(root, element_id, new_text, length=0):
    if isinstance(new_text, int):
        new_text = f"{'{:,}'.format(new_text)}"
    new_text = str(new_text)
    find_and_replace(root, element_id, new_text)
    just_len = max(0, length - len(new_text))
    if just_len <= 2:
        dot_map = {0: '', 1: ' ', 2: '. '}
        dot_string = dot_map[just_len]
    else:
        dot_string = ' ' + ('.' * just_len) + ' '
    find_and_replace(root, f"{element_id}_dots", dot_string)

def find_and_replace(root, element_id, new_text):
    element = root.find(f".//*[@id='{element_id}']")
    if element is not None:
        element.text = new_text


if __name__ == '__main__':
    """
    Christopher Milbourne (cmm21), 2022-2025
    """
    print('Calculation times:')
    # define global variable for owner ID and calculate user's creation date
    # e.g {'id': 'MDQ6VXNlcjU3MzMxMTM0'} and 2019-11-03T21:15:07Z for username 'cmm21'
    user_data, user_time = perf_counter(user_getter, USER_NAME)
    OWNER_ID, acc_date = user_data
    acc_datetime = datetime.datetime.strptime(acc_date, "%Y-%m-%dT%H:%M:%SZ")
    formatter('account data', user_time)
    age_data, age_time = perf_counter(daily_readme, acc_datetime)
    formatter('age calculation', age_time)
    (commit_data, total_prs, total_reviews), query_time = perf_counter(get_total_contributions, acc_datetime)
    formatter('contributions calculation', query_time)

    import glob
    for svg_file in glob.glob('*.svg'):
        svg_overwrite(svg_file, age_data, commit_data, total_prs, total_reviews, acc_datetime)

    print('',
        '{:<21}'.format('Total function time:'), '{:>11}'.format('%.4f' % (user_time + age_time + query_time)),
        ' s \033[E\033[E\033[E\033[E\033[E\033[E\033[E\033[E', sep=''
    )

    print('Total GitHub GraphQL API calls:', '{:>3}'.format(sum(QUERY_COUNT.values())))
    for funct_name, count in QUERY_COUNT.items(): print('{:<28}'.format('   ' + funct_name + ':'), '{:>6}'.format(count))

