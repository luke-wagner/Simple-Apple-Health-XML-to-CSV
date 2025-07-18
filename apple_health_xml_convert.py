#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple Apple Health XML to CSV
==============================
:File: convert.py
:Description: Convert Apple Health "export.xml" file into a csv
:Version: 0.0.2
:Created: 2019-10-04
:Updated: 2025-07-01
:Authors: Jason Meno (jam), Luke Wagner
:Dependencies: An export.xml file from Apple Health
:License: BSD-2-Clause
"""

# %% Imports
import os
import pandas as pd
import xml.etree.ElementTree as ET
import datetime as dt
import sys


# %% Function Definitions

def preprocess_to_temp_file(file_path):
    """
    The export.xml file is where all your data is, but Apple Health Export has
    two main problems that make it difficult to parse: 
        1. The DTD markup syntax is exported incorrectly by Apple Health for some data types.
        2. The invisible character \x0b (sometimes rendered as U+000b) likes to destroy trees. Think of the trees!

    Knowing this, we can save the trees and pre-processes the XML data to avoid destruction and ParseErrors.
    """

    print("Pre-processing and writing to temporary file...", end="")
    sys.stdout.flush()

    temp_file_path = "temp_preprocessed_export.xml"
    with open(file_path, 'r', encoding='UTF-8') as infile, open(temp_file_path, 'w', encoding='UTF-8') as outfile:
        skip_dtd = False
        for line in infile:
            if '<!DOCTYPE' in line:
                skip_dtd = True
            if not skip_dtd:
                line = strip_invisible_character(line)
                outfile.write(line)
            if ']>' in line:
                skip_dtd = False

    print("done!")
    return temp_file_path

def strip_invisible_character(line):
    return line.replace("\x0b", "")


def xml_to_csv(file_path):
    """Loops through the element tree, retrieving all objects, and then
    combining them together into a dataframe
    """

    print("Converting XML File to CSV...", end="")
    sys.stdout.flush()

    attribute_list = []

    for event, elem in ET.iterparse(file_path, events=('end',)):
        if event == 'end':
            child_attrib = elem.attrib
            for metadata_entry in list(elem):
                metadata_values = list(metadata_entry.attrib.values())
                if len(metadata_values) == 2:
                    metadata_dict = {metadata_values[0]: metadata_values[1]}
                    child_attrib.update(metadata_dict)
            attribute_list.append(child_attrib)

            # Clear the element from memory to avoid excessive memory consumption
            elem.clear()

    health_df = pd.DataFrame(attribute_list)

    # Every health data type and some columns have a long identifer
    # Removing these for readability
    health_df.type = health_df.type.str.replace('HKQuantityTypeIdentifier', "")
    health_df.type = health_df.type.str.replace('HKCategoryTypeIdentifier', "")
    health_df.columns = \
        health_df.columns.str.replace("HKCharacteristicTypeIdentifier", "")

    # Reorder some of the columns for easier visual data review
    original_cols = list(health_df)
    shifted_cols = ['type',
                    'sourceName',
                    'value',
                    'unit',
                    'startDate',
                    'endDate',
                    'creationDate']

    # Add loop specific column ordering if metadata entries exist
    if 'com.loopkit.InsulinKit.MetadataKeyProgrammedTempBasalRate' in original_cols:
        shifted_cols.append(
            'com.loopkit.InsulinKit.MetadataKeyProgrammedTempBasalRate')

    if 'com.loopkit.InsulinKit.MetadataKeyScheduledBasalRate' in original_cols:
        shifted_cols.append(
            'com.loopkit.InsulinKit.MetadataKeyScheduledBasalRate')

    if 'com.loudnate.CarbKit.HKMetadataKey.AbsorptionTimeMinutes' in original_cols:
        shifted_cols.append(
            'com.loudnate.CarbKit.HKMetadataKey.AbsorptionTimeMinutes')

    remaining_cols = list(set(original_cols) - set(shifted_cols))
    reordered_cols = shifted_cols + remaining_cols
    health_df = health_df.reindex(labels=reordered_cols, axis='columns')

    # Sort by newest data first
    health_df.sort_values(by='startDate', ascending=False, inplace=True)

    print("done!")

    return health_df


def extract_biometrics_data(df):
    """
    Given a dataframe of the complete health data, extract only the biometrics data and return 
    this as a new dataframe

    Want to get a listing of all metrics recorded by smart scale, then get a complete history
    for all of these metrics. Essentially, "Get all entries where type in 
    (get distinct type where source == RENPHO smart scale)"
    """
    # Step 1: Get the distinct type values where sourceName == "RENPHO Health"
    types_to_keep = df.loc[df["sourceName"] == "RENPHO Health", "type"].unique()

    # Step 2: Filter the DataFrame to rows where type is in types_to_keep
    filtered_df = df[df["type"].isin(types_to_keep)]

    # Order by type then date
    filtered_df = filtered_df.sort_values(by=["type", "creationDate"], ascending=[True, False])

    return filtered_df


def save_to_csv(df, filename_prefix):
    print("Saving CSV file...", end="")
    sys.stdout.flush()

    today = dt.datetime.now().strftime('%Y-%m-%d')
    df.to_csv(filename_prefix + "_" + today + ".csv", index=False)
    print("done!")

    return

def remove_temp_file(temp_file_path):
    print("Removing temporary file...", end="")
    os.remove(temp_file_path)
    print("done!")
    
    return

def main():
    file_path = "export.xml"
    temp_file_path = preprocess_to_temp_file(file_path)
    health_df = xml_to_csv(temp_file_path)
    save_to_csv(health_df, "apple_health_export")
    biometrics_df = extract_biometrics_data(health_df)
    save_to_csv(biometrics_df, "biometrics_export")
    remove_temp_file(temp_file_path)

    return


# %%
if __name__ == '__main__':
    main()
