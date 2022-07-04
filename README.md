# dt_measurements

## Structure

Every measurement is placed in a seperated directory and consits of the following:
* `*.json` Downloaded json objected form TTN formated in a list to preserve cronology.
* `analyze.py` an executable script which reads all the messages, analyzes it and gives some plots.

* `helper.py` in the root-dir is used to do the calculations
* `combine.py` can be used to format the raw data downloaded from TTN to the format in use (list of dicts), also it can be used to combine 2 json files (duplicates are removed automatically)

## Usage

Be sure to have `numpy` and `matplotlib` installed, everything else should have been shipped with python3 directly.

Afterwards simply go to directory and run:

`python3 analyze.py`

In order to have an easy way of generating the plots for the diploma-thesis `thesisplot.py` can be used to regenerate all the plots used in the thesis.
