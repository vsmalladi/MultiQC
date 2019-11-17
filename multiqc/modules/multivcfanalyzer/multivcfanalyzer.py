#!/usr/bin/env python

""" MultiQC module to parse output from MultiVCFAnalyzer """

from __future__ import print_function
from collections import OrderedDict
import logging
import json

from multiqc.plots import table
from multiqc.plots import bargraph
from collections import OrderedDict
from multiqc.modules.base_module import BaseMultiqcModule

# Initialise the logger
log = logging.getLogger(__name__)

class MultiqcModule(BaseMultiqcModule):
    """ MultiVCFAnalyzer module """

    def __init__(self):

        # Initialise the parent object
        super(MultiqcModule, self).__init__(name='MultiVCFAnalyzer', anchor='multivcfanalyzer',
        href="https://github.com/alexherbig/MultiVCFAnalyzer",
        info="""combines multiple VCF files in a coherent way, can produce summary statistics and downstream analysis formats for phylogeny reconstruction.""")

        # Find and load any MultiVCFAnalyzer reports
        self.mvcf_data = dict()

        # Find and load JSON file
        for f in self.find_log_files('multivcfanalyzer', filehandles=True):
            self.parse_data(f)

        # Filter samples
        self.mvcf_data = self.ignore_samples(self.mvcf_data)

        # Return if no samples found
        if len(self.mvcf_data) == 0:
            raise UserWarning

        # Add in extra columns to data file
        self.compute_perc_hets()

        # Save data output file
        self.write_data_file(self.mvcf_data, 'multiqc_multivcfanalyzer')

        # Add to General Statistics
        self.addSummaryMetrics()

        # Add MultiVCFAnalyzer Table Section
        self.add_section (
        name = 'MultiVCFAnalyzer analysis results',
        anchor = 'mvcf_table',
        helptext = "This is the output from MultiVCFAnalyzer. Please refer to the manual here - https://github.com/alexherbig/MultiVCFAnalyzer for more information on how to interpret data.",
        plot = self.addTable())
        
        # Add MultiVCFAnalyzer Barplot Section
        self.add_section (
        name = 'Call statistics barplot',
        anchor = 'mvcf-barplot',
        plot = self.addBarplot()
        )


    def parse_data(self, f):
        try:
            data = json.load(f['f'])
        except Exception as e:
            log.debug(e)
            log.warn("Could not parse MultiVCFAnalyzer JSON: '{}'".format(f['fn']))
            return

        # Parse JSON data to a dict
        for s_name, metrics in data.get('metrics', {}).items():
            s_clean = self.clean_s_name(s_name, f['root'])
            if s_clean in self.mvcf_data:
                log.debug("Duplicate sample name found! Overwriting: {}".format(s_clean))

            self.add_data_source(f, s_clean)
            self.mvcf_data[s_clean] = dict()           
            for snp_prop, value in metrics.items():
                self.mvcf_data[s_clean][snp_prop] = value

    #Compute % heterozygous snp alleles and add to data
    def compute_perc_hets(self):
        """Take the parsed stats from MultiVCFAnalyzer and add one column per sample """
        for sample in self.mvcf_data:
            try:
                self.mvcf_data[sample]['Heterozygous SNP alleles (percent)'] = (self.mvcf_data[sample]['SNP Calls (het)'] / self.mvcf_data[sample]['SNP Calls (all)'])*100
            except ZeroDivisionError:
                self.mvcf_data[sample]['Heterozygous SNP alleles (percent)'] = 'NA'

    def addSummaryMetrics(self):
        """ Take the parsed stats from MultiVCFAnalyzer and add it to the main plot """

        headers = OrderedDict()
        headers['SNP Calls (all)'] = {
            'title': 'SNPs',
            'description': 'Total number of non-reference calls made',
            'scale': 'OrRd',
            'shared_key': 'snp_call'
        }
        headers['SNP Calls (het)'] = {
            'title': 'Het SNPs',
            'description': 'Total number of non-reference calls not passing homozygosity thresholds',
            'scale': 'OrRd',
            'hidden': True,
            'shared_key': 'snp_call'
        }
        headers['Heterozygous SNP alleles (percent)'] = {
            'title': '% Hets',
            'description': 'Percentage of heterozygous SNP alleles',
            'scale': 'OrRd',
            'shared_key': 'snp_call'
        }
        self.general_stats_addcols(self.mvcf_data, headers)

    def addTable(self):
        """ Take the parsed stats from MultiVCFAnalyzer and add it to the MVCF Table"""
        headers = OrderedDict()

        headers['allPos'] = {
            'title': 'Bases in SNP Alignment',
            'description': 'Length of FASTA file in base pairs (bp)',
            'scale': 'BuPu',
            'shared_key': 'calls'
        }
        headers['discardedVarCall'] = {
            'title': 'Discarded SNP Call',
            'description': 'Number of non-reference positions not reaching genotyping quality threshold',
            'scale': 'BuPu',
            'hidden': True,
            'shared_key': 'calls'
        }
        headers['filteredVarCall'] = {
            'title': 'Filtered SNP Call',
            'description': 'Number of positions ignored defined in user-supplied filter list',
            'scale': 'BuPu',
            'hidden': True,
            'shared_key': 'calls'
        }
        headers['refCall'] = {
            'title': 'Number of Reference Calls',
            'description': 'Number of reference calls made',
            'scale': 'BuPu',
            'hidden': True,
            'shared_key': 'calls'
        }
        headers['discardedRefCall'] = {
            'title': 'Discarded Reference Call',
            'description': 'Number of reference positions not reaching genotyping quality threshold',
            'scale': 'BuPu',
            'hidden': True,
            'shared_key': 'calls'
        }
        headers['noCall'] = {
            'title': 'Positions with No Call',
            'description': 'Number of positions with no call made as reported by GATK',
            'scale': 'BuPu',
            'shared_key': 'calls'
        }
        headers['coverage (fold)'] = {
            'title': 'SNP Coverage',
            'description': 'Average number of reads covering final calls',
            'scale': 'OrRd',
            'shared_key': 'coverage'
        }
        headers['coverage (percent)'] = {
            'title': '% SNPs Covered',
            'description': 'Percent coverage of all positions with final calls',
            'scale': 'PuBuGn',
            'shared_key': 'coverage'
        }
        headers['unhandledGenotype'] = {
            'title': 'Unhandled Genotypes',
            'description': 'Number of positions discarded due to presence of more than one alternate allele',
            'scale': 'BuPu',
            'hidden': True,
            'shared_key': 'snp_count'
        }

        #Separate table config
        table_config = {
        'namespace': 'MultiVCFAnalyzer',                         # Name for grouping. Prepends desc and is in Config Columns modal
        'id': 'mvcf-table',                 # ID used for the table
        'table_title': 'MultiVCFAnalyzer Results',             # Title of the table. Used in the column config modal
        }
        tab = table.plot(self.mvcf_data, headers, table_config)
        return tab


    def addBarplot(self):
        """ Take the parsed stats from MultiVCFAnalyzer and add it to the MVCF Table"""
        cats = OrderedDict()
        cats['SNP Calls (all)'] = {
            'name': 'SNP Calls (all)',
            'description': 'Total number of non-reference calls made',
            'color': '#8bbc21'
        }
        cats['discardedVarCall'] = {
            'name': 'Discarded SNP Call',
            'description': 'Number of non-reference positions not reaching genotyping quality threshold',
            'color': '#f7a35c'
        }
        cats['filteredVarCall'] = {
            'name': 'Filtered SNP Call',
            'description': 'Number of positions ignored defined in user-supplied filter list',
            'scale': 'BuPu'
        }
        cats['refCall'] = {
            'name': 'Number of Reference Calls',
            'description': 'Number of reference calls made',
            'scale': 'BuPu'
        }
        cats['discardedRefCall'] = {
            'name': 'Discarded Reference Call',
            'description': 'Number of reference positions not reaching genotyping quality threshold',
            'scale': 'BuPu'
        }
        cats['noCall'] = {
            'name': 'Positions with No Call',
            'description': 'Number of positions with no call made as reported by GATK',
            'scale': 'BuPu'
        }

        config = {
        # Building the plot
        'id': 'mvcf_barplot',                # HTML ID used for plot
        'hide_zero_cats': True,                 # Hide categories where data for all samples is 0
        # Customising the plot
        'title': 'MultiVCFAnalyzer: Call Categories',                          # Plot title - should be in format "Module Name: Plot Title"
        'ylab': 'Total # Positions',                           # X axis label
        'xlab': None,
        'stacking': 'normal',                   # Set to None to have category bars side by side
        'use_legend': True,                     # Show / hide the legend
        }
        return bargraph.plot(self.mvcf_data, cats, config)
        