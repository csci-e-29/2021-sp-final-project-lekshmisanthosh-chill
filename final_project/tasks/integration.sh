conda create -n integration_env -y -q python=3.8 luigi
eval "$(conda shell.bash hook)"
conda run -n integration_env python --version
conda run -n integration_env python -m pip install pandas dask
conda run -n integration_env python -m pip install -e git+https://github.com/csci-e-29/2021sp-csci-utils-lekshmisanthosh-chill#egg=csci_utils
conda run -n integration_env python microservices/tasks/tasks.py
conda deactivate
conda env remove -n integration_env
rm -r data/covid_data
echo "Finished data generation!!"