#!/bin/bash

kaggle competitions download -c h-and-m-personalized-fashion-recommendations -f articles.csv
kaggle competitions download -c h-and-m-personalized-fashion-recommendations -f customers.csv
kaggle competitions download -c h-and-m-personalized-fashion-recommendations -f transactions_train.csv

unzip -o articles.csv
unzip -o customers.csv
unzip -o transactions_train.csv
