# Semantic Frame Identification

## Prerequisites

Create and setup the environment

> conda env create -f environment.yml

> python -m nltk.downloader framenet_v17

## Running the code

> python3 src/main.py [OPTIONS]

```
  --batch-size N        input batch size for training (default: 64)
  --test                disables training, loads model
  --network [{Simple,Epic,Bonus}]
                        Choose the type of network from Simple, Epic and Bonus
                        (default: Epic)
  --epochs N            number of epochs to train (default: 10)
  --lr LR               learning rate (default: 0.01)
  --momentum M          SGD momentum (default: 0.5)
  --step N              number of epochs to decrease learn-rate (default: 3)
  --gamma N             factor to decrease learn-rate (default: 0.1)

```

## Examples

To run test on Simple Network

> python3 src/main.py --test

To run test on Network with attention

> python3 src/main.py --test --attention

## Hyperparameters

### LSTM
```bash
batch_size=64 
hidden_size=128
num_layers=1
epochs=15
```


