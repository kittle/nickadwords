#!/usr/bin/python

import os
import sys
import getopt
import types

from json import loads, dumps
from pprint import pprint, PrettyPrinter
from adspygoogle.adwords.AdWordsClient import AdWordsClient
from adspygoogle.common import Utils
from adspygoogle.adwords.AdWordsErrors import AdWordsRequestError

DEBUG = True
adwords_api_server = 'https://adwords.google.com' # 'https://adwords-sandbox.google.com'


def get_client():
    return AdWordsClient(path=".")


def add_campaign(client, name, enddate = '20110101', budgetmicroamount = '9000000'):
    campaign_service = client.GetCampaignService(adwords_api_server, 'v201003')
    operations = [{
        'operator': 'ADD',
        'operand': {
            'name': name,
            'status': 'PAUSED',
            'biddingStrategy': {
                'type': 'ManualCPC'
            },
            'endDate': enddate,
            'budget': {
                'period': 'DAILY',
                'amount': {
                    'microAmount': budgetmicroamount
                },
                'deliveryMethod': 'STANDARD'
            }
        }
    }]
    campaigns = campaign_service.Mutate(operations)[0]
    
    if DEBUG:
        for campaign in campaigns['value']:
            print >> sys.stderr, ("Campaign with name '%s' and id '%s' was added."
                 % (campaign['name'], campaign['id']))
    return campaigns['value'][0]['id']
        
        
def get_campaigns(client):
    campaign_service = client.GetCampaignService(adwords_api_server, 'v201003')
    
    selector = {}
    campaigns = campaign_service.Get(selector)[0]
    
    if 'entries' in campaigns:
        return campaigns['entries']
    else:
        return []
    
    
def get_all_ad_groups_by_campaign_id(client, campaign_id):
    ad_group_service = client.GetAdGroupService(adwords_api_server, 'v201003')
    
    selector = {
        'campaignIds': [campaign_id]
    }
    ad_groups = ad_group_service.Get(selector)[0]
    
    if 'entries' in ad_groups:
        return ad_groups['entries']
    else:
        return []


def print_ad_groups_by_ad_groups(ad_groups):
    if ad_groups:
        for ad_group in ad_groups:
            print ('Ad group with name \'%s\', id \'%s\', and status \'%s\' was found.'
                   % (ad_group['name'], ad_group['id'], ad_group['status']))
    else:
        print 'No ad groups were found.'        


def add_ad_groups(client, adgroups):
    ad_errors = []
    
    ad_group_service = client.GetAdGroupService(adwords_api_server, 'v201003')

    operations = map(lambda ad_group: 
        {
            'operator': 'ADD',
            'operand': {
                'campaignId': ad_group['campaign_id'],
                'name': ad_group['name'],
                'status': 'ENABLED',
                # WARNING: bids here do nothing
                'bids': {
                    'type': 'ManualCPCAdGroupBids',
                    'keywordMaxCpc': {
                        'amount': {
                            'microAmount': ad_group['MaxCpcmicroAmount'] # Amount in micros. One million is equivalent to one unit.
                            #'microAmount': '777777'   # NO
                            #'microAmount': '777700'   # NO
                            #'microAmount': '777000'   # NO
                            #'microAmount': '770000'   # YES
                            #'microAmount': '500000'   # YES
                        }
                    }
                }
            }
        }, adgroups)    

    try:
        ad_groups = ad_group_service.Mutate(operations)[0]
    except AdWordsRequestError, e:
        for error in e.errors:
            #print error.__dict__
            ad_errors.append({'ad_group': error.trigger,
                                              'error': error.errorString,
                                              'field': error.fieldPath})
        return [], ad_errors
    
    if DEBUG:
        for ad_group in ad_groups['value']:
            print >> sys.stderr, ('Ad group with name \'%s\' and id \'%s\' was added.'
                 % (ad_group['name'], ad_group['id']))
    return ad_groups['value'], ad_errors


def update_status_ad_groups(client, ad_group_ids, status):
    ad_group_service = client.GetAdGroupService(adwords_api_server, 'v201003')

    operations = map(lambda ad_group_id: 
        {
            'operator': 'SET',
            'operand': {
                'id': ad_group_id,
                'status': status
            }
        } , ad_group_ids)

    ad_groups = ad_group_service.Mutate(operations)[0]
    
    if DEBUG:
        for ad_group in ad_groups['value']:
            print >> sys.stderr, ('Ad group with name \'%s\' and id \'%s\' was updated.'
                 % (ad_group['name'], ad_group['id']))

"""
def update_bids_ad_groups(client, ad_group_ids, MaxCpcmicroAmount):
    "trying to make maxcpc woraround. NEGATIVE"
    ad_group_service = client.GetAdGroupService(adwords_api_server, 'v201003')

    operations = map(lambda ad_group_id: 
        {
            'operator': 'SET',
            'operand': {
                'id': ad_group_id,
                'bids': {
                    'type': 'ManualCPCAdGroupBids',
                    'keywordMaxCpc': {
                        'amount': {
                            'microAmount': MaxCpcmicroAmount
                        }
                    }
                }
            }
        } , ad_group_ids)

    ad_groups = ad_group_service.Mutate(operations)[0]
    
    if DEBUG:
        for ad_group in ad_groups['value']:
            print >> sys.stderr, ('Ad group with name \'%s\' and id \'%s\' was updated.'
                 % (ad_group['name'], ad_group['id']))
"""


def pause_ad_groups(client, ad_group_ids):
    return update_status_ad_groups(client, ad_group_ids, 'PAUSED')


#def enable_ad_groups(client, ad_group_ids):
#    return update_status_ad_groups(client, ad_group_ids, 'ENABLED')


def delete_ad_groups(client, ad_group_ids):
    return update_status_ad_groups(client, ad_group_ids, 'DELETED')


def add_ad_group_criterias(client, operations):
    ad_group_criterion_service = client.GetAdGroupCriterionService(
                                                                   adwords_api_server, 'v201003')
    ad_group_criteria = ad_group_criterion_service.Mutate(operations)[0]['value']

    if DEBUG:
        for criterion in ad_group_criteria:
            if criterion['criterion']['Criterion_Type'] == 'Keyword':
                print >> sys.stderr, ('Keyword ad group criterion with ad group id \'%s\', criterion id '
                   '\'%s\', text \'%s\', and match type \'%s\' was added.'
                   % (criterion['adGroupId'], criterion['criterion']['id'],
                      criterion['criterion']['text'],
                      criterion['criterion']['matchType']))


def add_textads(client, textads):
    ad_group_ad_service = client.GetAdGroupAdService(adwords_api_server, 'v201003')
    operations = map(lambda textad:
         {
            'operator': 'ADD',
            'operand': {
                'type': 'AdGroupAd',
                'adGroupId': textad['ad_group_id'],
                'ad': {
                    'type': 'TextAd',
                    'url': textad['url'],
                    'displayUrl': textad['displayurl'],
                    'status': 'ENABLED',
                    'description1': textad['description1'],
                    'description2': textad['description2'],
                    'headline': textad['headline'],
                }
            }
         }, textads)
    ads = ad_group_ad_service.Mutate(operations)[0]
    
    if DEBUG:
        for ad in ads['value']:
            print >> sys.stderr, ('Ad with id \'%s\' and of type \'%s\' was added.'
                 % (ad['ad']['id'], ad['ad']['Ad_Type']))

    ads_ids = map(lambda ad: ad['ad']['id'], ads['value'])
    return ads_ids


def get_report(client, report_definition_id):
    report_definition_service = client.GetReportDefinitionService(adwords_api_server, 'v201003')
    return report_definition_service.DownloadReport(report_definition_id)


def get_all_report_definitions(client):
    report_definition_service = client.GetReportDefinitionService(adwords_api_server, 'v201003')
    
    selector = {}
    report_definitions = report_definition_service.Get(selector)[0]
    
    if 'entries' in report_definitions:
        if DEBUG:
            for report_definition in report_definitions['entries']:
                print >> sys.stderr, ('Report definition with name \'%s\' and id \'%s\' was found.'
                       % (report_definition['reportName'], report_definition['id']))
        return report_definitions['entries']
    else:
        if DEBUG:
            print >> sys.stderr, 'No report definitions were found.'
        return []


def print_report_fields(client, report_type):
    report_definition_service = client.GetReportDefinitionService(adwords_api_server, 'v201003')
    fields = report_definition_service.GetReportFields(report_type)
    print 'Report type \'%s\' contains the following fields:' % report_type
    for field in fields:
        print ' - %s (%s)' % (field['fieldName'], field['fieldType'])
        if field.has_key('enumValues'):
            print '  := [%s]' % ', '.join(field['enumValues'])

    field_names = map(lambda x: x['fieldName'], fields)
    return field_names


def add_report_definition(client, report_name):
    report_definition_service = client.GetReportDefinitionService(adwords_api_server, 'v201003')    
    operations = [{
        'operator': 'ADD',
        'operand': {
            'type': 'ReportDefinition',
            'reportName': report_name,
            'dateRangeType': 'ALL_TIME',
            'reportType': 'KEYWORDS_PERFORMANCE_REPORT',
            'downloadFormat': 'CSV',
            'selector': {
                    'fields': [
                        'AdGroupId',
                        'AdGroupName',
                        'AdGroupStatus',
                        'AdNetworkType1',
                        'AdNetworkType2',
                        'AverageCpc',
                        'AverageCpm',
                        'AveragePosition',
                        'BottomPosition',
                        'CampaignId',
                        'CampaignName',
                        'CampaignStatus',
                        'Clicks',
                        'ClickType',
                        'ConversionRate',
                        'ConversionRateManyPerClick',
                        'Conversions',
                        'ConversionsManyPerClick',
                        'ConversionValue',
                        'Cost',
                        'CostPerConversion',
                        'CostPerConversionManyPerClick',
                        'CriteriaDestinationUrl',
                        'Ctr',
                        'Date',
                        'DayOfWeek',
                        'DestinationUrl',
                        'FirstPageCpc',
                        'Id',
                        'Impressions',
                        'IsNegative',
                        'KeywordMatchType',
                        'KeywordText',
                        'MaxCpc',
                        'MaxCpm',
                        'Month',
                        'MonthOfYear',
                        'PlacementUrl',
                        'PreferredPosition',
                        'ProxyMaxCpc',
                        'QualityScore',
                        'Quarter',
                        'Status',
                        'TotalConvValue',
                        'ValuePerConv',
                        'ValuePerConversion',
                        'ValuePerConversionManyPerClick',
                        'ValuePerConvManyPerClick',
                        'ViewThroughConversions',
                        'Week',
                        'Year']
            }
        }
    }]
    report_definitions = report_definition_service.Mutate(operations)
    
    if DEBUG:
        for report_definition in report_definitions:
            print >> sys.stderr, ('Report definition with name \'%s\' and id \'%s\' was added'
                                  % (report_definition['reportName'], report_definition['id']))

    return report_definitions[0]['id']


def delete_report_definition(client, report_definitions_id):
    report_definition_service = client.GetReportDefinitionService(
                                                                  adwords_api_server, 'v201003')    
    operations = [{
        'operator': ' REMOVE',
        'operand': {
            'id': report_definitions_id,
        }
    }]
    report_definitions = report_definition_service.Mutate(operations)
    
    if DEBUG:
        for report_definition in report_definitions:
            print >> sys.stderr, ('Report definition with name \'%s\' and id \'%s\' was deleted'
                 % (report_definition['reportName'], report_definition['id']))


adwords_language_target_serach_paramater = {
      'type': 'LanguageTargetSearchParameter' ,
      'languageTargets': [
              {
                  'type': 'LanguageTarget',
                  'languageCode': 'en'
              }
      ]
}

def get_related_keywords(client, keywords, startindex=0, numberresults=800):
    assert type(keywords) == types.ListType or type(keywords) == types.TupleType

    targeting_idea_service = client.GetTargetingIdeaService(adwords_api_server, 'v201003')

    selector = {
                'searchParameters': [
                              {
                                    'type': 'RelatedToKeywordSearchParameter' ,
                                    'keywords': [
                                        {
                                             'text': keyword,
                                             'matchType': 'EXACT'
                                        } for keyword in keywords
                                    ]
                              },
                              adwords_language_target_serach_paramater
                        ], 
                        'ideaType': 'KEYWORD',
                        'requestType': 'IDEAS',
                        'paging': {
                            'startIndex': str(startindex),
                            'numberResults': str(numberresults)
                        }
                    }

    page = targeting_idea_service.Get(selector)[0]
    return page


def get_related_urls(client, urls, startindex=0, numberresults=800):
    assert type(urls) == types.ListType
    
    targeting_idea_service = client.GetTargetingIdeaService(adwords_api_server, 'v201003')

    selector = {
                'searchParameters': [
                              {
                                    'type': 'RelatedToUrlSearchParameter' ,
                                    'urls': urls
                              },
                              adwords_language_target_serach_paramater
                        ], 
                        'ideaType': 'KEYWORD',
                        'requestType': 'IDEAS',
                        'paging': {
                            'startIndex': str(startindex),
                            'numberResults': str(numberresults)
                        }
                    }

    page = targeting_idea_service.Get(selector)[0]
    return page


def get_values_from_page(page):
    ks = []
    #total = 0
    if 'entries' in page:
        for result in page['entries']:
            assert len(result['data'][0]['value']) == 1
            result = result['data'][0]['value'][0]
            ks.append(result['value'][0]['text'])
        """
            print ('Keyword with \'%s\' text and \'%s\' match type is found.'
                       % (result['value'][0]['text'], result['value'][0]['matchType']))
        """
        #total = page['totalNumEntries']
    #return {'total': total, 'entries': ks}
    return ks


def client_usage(client):
    print ('Usage: %s units, %s operations' % (client.GetUnits(), client.GetOperations()))


def main_fields():
    client = get_client()
    print_report_fields(client, "KEYWORDS_PERFORMANCE_REPORT")
    
    
def main_add_report():
    client = get_client()
    print get_all_report_definitions(client)
    report_definition_id = add_report_definition(client, 'Nick_allcol')
    print report_definition_id


def main_campaigns():
    client = get_client()
    campaigns = get_campaigns(client)
    for campaign in campaigns:
        out = "CMP:\t" + campaign['id'] + "\t" + campaign["name"]
        print out


def main_report():
    client = get_client()
    
    report_definition_id = 7990727 # Nick_allcol
    data = get_report(client, report_definition_id)
    print data


def main_json():
    data = sys.stdin.read()
    g = loads(data)
 
    client = get_client()

    # create ad groups
    if g.get("create"):
        assert g.get("create_campaign_id")
        pprint(g["create"])
        ad_groups = map(lambda x:
            {'campaign_id': g["create_campaign_id"],
             'name': x['code'],
             #'MaxCpcmicroAmount': str(x['cpc'] * 1000000)  # NOT THIS WAY !!!
             'MaxCpcmicroAmount': str(x['cpc']*100).split(".")[0] + '0000'  # cents only
             }, g["create"])
            
        print "ad_groups len: %s" % len(ad_groups)
        pprint(ad_groups)
        
        # names here must be unique
        ad_group_names = map(lambda x: x['name'], ad_groups)
        if len(list(set(ad_group_names))) != len(ad_group_names):
            raise Exception("ad_group_names is not unique ! %s" % str(ad_group_names))
        
        # create ad groups
        ts, ad_errors = add_ad_groups(client, ad_groups)
        if ad_errors:
            print dumps(ad_errors)
            return
        
        ad_groups_map = {}
        for t in ts:
            ad_groups_map[t['name']] = t['id']
        print "ad_groups_map len: %s" % len(ad_groups_map)
        pprint(ad_groups_map)
    
        # test
        #update_bids_ad_groups(client, map(lambda x:x['id'], ts), "777777.0")
    
        # create textads
        textads = []

        # add criteria
        ad_group_criterias = []

        for adgroup in g["create"]:
            # TODO: move to  add_ad_group_criterias
            ad_group_criterias.extend(
                map(lambda keyword: 
                   {
                        'operator': 'ADD',
                        'operand': {
                            'type': 'BiddableAdGroupCriterion',
                            'adGroupId': ad_groups_map[adgroup['code']],
                            'criterion': {
                                'type': 'Keyword',
                                'matchType': 'BROAD',
                                'text': keyword
                             }
                             # WARNING: bids here is workaround for non worked adgroup bids
#                             ,
#                            'bids': {
#                                'type': 'ManualCPCAdGroupCriterionBids',
#                                'maxCpc': {
#                                    'amount': {
#                                        #'microAmount': str(adgroup['cpc'] * 1000000)
#                                        'microAmount': '500000'
#                                     }
#                                 }
#                             }
                         }
                   }, adgroup['keywords'])        
            )
            textads.extend(
                map(lambda ad: 
                   {'headline': ad['hline'],
                   'description1': ad['dline1'],
                   'description2': ad['dline2'],
                   'displayurl': ad['dispurl'],
                   'url': ad['desturl'],
                   'ad_group_id': ad_groups_map[adgroup['code']]
                   } , adgroup['ads']
                )
            )                       
        print "ad_group_criterias len: %s" % len(ad_group_criterias)
        pprint(ad_group_criterias)
        add_ad_group_criterias(client, ad_group_criterias)

        print "textads len: %s" % len(textads)
        pprint(textads)
        textad_ids = add_textads(client, textads)
        print "added textad_ids %s" % textad_ids

    if g.get("suspend"): pause_ad_groups(client, g["suspend"])
    if g.get("delete"): delete_ad_groups(client, g["delete"])
    #if g.get("enable"): enable_ad_groups(client, g["enable"])
    

def main_related_ideas(f):
    data = loads(sys.stdin.read())
    client = get_client()
    page = f(client, data)
    ret = get_values_from_page(page)
    print dumps(ret)


def playground():
    #client = get_client()
    #pprint(get_related_keywords(client, (zuka", "buka")))
    #pprint(get_related_keywords(client, ("buka",)))
    #page = get_related_urls(client, ["http://habrahabr.ru",])
    #pprint(page)
    #pprint(get_values_from_page(page))
    #    print get_values_from_page(page)
    
    #keywords = [ "stone \\ Racing - Experiment", ]
    #page = get_related_keywords(client, keywords)
    
    #pprint(page)
    # return
    
    """
    pp = PrettyPrinter()
 
    campaigns = get_campaigns(client)
    pprint(campaigns)
    out = ""
    for campaign in campaigns:
        out += campaign['id'] + "\t"
        out += pp.pformat(campaign) + "\n"
        ad_groups = get_all_ad_groups_by_campaign_id(client, campaign['id'])
        out += pp.pformat(ad_groups)
        out += "\n\n"
        #break
    print out
    open("/tmp/pp.txt", "w").write(out)
    """
    
    # add campaign
    #campaign_id = add_campaign(client, name = 'kittle test camp')
    #print campaign_id
    #return
    
    #campaign_id = 60457695 # for PlayGameClub
    campaign_id = 59586287 # for Stone Dam
    
    #add ad_group
    adgroups = [{'campaign_id': campaign_id,
                 'name': 'ad_group1',
                 'MaxCpcmicroAmount': "1000000"},]
    # t = add_ad_groups(client, adgroups)
    # ad_group_ids = map(t
    #ad_group_id = 1846142655
    
    ad_group_id = 1655988527
    
    # add textads
    textads = [
                   {'headline': 'zuka1',
                   'description1': 'buka1',
                   'description2': 'buka2',
                   'displayurl':'http://zukabuka.com',
                   'url': 'http://zukabuka.com',
                   'ad_group_id': ad_group_id},
                   {'headline': 'zuka2',
                   'description1': 'buka21',
                   'description2': 'buka22',
                   'displayurl':'http://zukabuka2.com',
                   'url': 'http://zukabuka2.com',
                   'ad_group_id': ad_group_id},
                ]
    #ads_ids = add_textads(client, ad_group_id, textads)
    #print ads_ids
    #ads_ids = ['5853520455', '5853520575']

    #ad_group_ids = [ad_group_id,]


def usage():
    print "Usage:   %s -a      - add report definition" % os.path.basename(sys.argv[0])
    print "Usage:   %s -c      - do campaigns list to stdout" % os.path.basename(sys.argv[0])
    print "Usage:   %s -r      - do report to stdout" % os.path.basename(sys.argv[0])
    print "Usage:   %s -j      - read json from stdin" % os.path.basename(sys.argv[0])
    print "Usage:   %s -f      - print report fields to stdout" % os.path.basename(sys.argv[0])
    print "Usage:   %s -e     - get related for keywords. stdin->stdout. json" % os.path.basename(sys.argv[0])
    print "Usage:   %s -u     - get related for urls. stdin->stdout. json" % os.path.basename(sys.argv[0])
    sys.exit(1)


if __name__ == '__main__':
    #playground()
    #sys.exit()
    
    # -a option removed to prevent accident addition of another
    # Nick_allcol report definition
    opts, args = getopt.getopt(sys.argv[1:], "crjfeu")
    for o, a in opts:
        if o == "-a":
            main_add_report()
            sys.exit()
        elif o == "-c":
            main_campaigns()
            sys.exit()
        elif o == "-r":
            main_report()
            sys.exit()
        elif o == "-j":
            main_json()
            sys.exit()
        elif o == "-f":
            main_fields()
            sys.exit()
        elif o == "-e":
            main_related_ideas(get_related_keywords)
            sys.exit()
        elif o == "-u":
            main_related_ideas(get_related_urls)
            sys.exit()
        else:
            raise Exception("Unknown filter %s" % a)

    usage()
