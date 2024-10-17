#!/bin/bash

results_dir="s3://modulome/results_v2/$1"
local_dir="aws_results"

if [[ ! -e $local_dir ]]; then
    mkdir $local_dir
fi

cd $local_dir

# Download data
aws s3 cp --recursive $results_dir/bowtie/ bowtie/
aws s3 cp --recursive $results_dir/fastqc/ fastqc/
aws s3 cp --recursive $results_dir/featureCounts/ featureCounts/
aws s3 cp --recursive $results_dir/rseqc/ rseqc/
aws s3 cp --recursive $results_dir/trim_reports/ trim_reports/

# Run multiqc
multiqc -f -c ../assets/multiqc_config.yaml .
python ../bin/assemble_qc_stats.py multiqc_data

# Get log_tpm
python ../bin/assemble_tpm.py -d featureCounts -o .

# Clean up
rm -r bowtie
rm -r fastqc
rm -r featureCounts
rm -r rseqc
rm -r trim_reports

cd ..
