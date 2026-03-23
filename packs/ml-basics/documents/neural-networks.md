# Neural Networks

Neural networks are computational models inspired by the structure of biological brains. They consist of layers of interconnected nodes (neurons) that process information by transforming inputs through learned weights and biases.

## Architecture

A typical neural network has three types of layers:

- **Input layer**: Receives the raw data (e.g., pixel values of an image or words in a sentence).
- **Hidden layers**: Perform intermediate computations. Deep networks have many hidden layers, enabling them to learn hierarchical representations.
- **Output layer**: Produces the final prediction, such as a class label or a numerical value.

Each connection between neurons has a weight that determines how strongly one neuron influences another. During training, these weights are adjusted to minimize prediction errors.

## Activation Functions

Activation functions introduce non-linearity, allowing networks to learn complex patterns:

- **ReLU (Rectified Linear Unit)**: Outputs the input directly if positive, otherwise outputs zero. Most commonly used in hidden layers.
- **Sigmoid**: Squashes values between 0 and 1. Useful for binary classification outputs.
- **Softmax**: Converts a vector of values into a probability distribution. Used in multi-class classification output layers.
- **Tanh**: Squashes values between -1 and 1. Sometimes preferred over sigmoid for hidden layers.

## Training with Backpropagation

Neural networks learn through a process called backpropagation:

1. **Forward pass**: Input data flows through the network to produce a prediction.
2. **Loss calculation**: The prediction is compared to the true label using a loss function (e.g., cross-entropy for classification, mean squared error for regression).
3. **Backward pass**: Gradients of the loss with respect to each weight are computed using the chain rule of calculus.
4. **Weight update**: Weights are adjusted in the direction that reduces the loss, typically using an optimizer like SGD or Adam.

## Common Architectures

- **Convolutional Neural Networks (CNNs)**: Specialized for grid-like data such as images. They use convolutional filters to detect local patterns like edges and textures.
- **Recurrent Neural Networks (RNNs)**: Designed for sequential data like text and time series. They maintain a hidden state that captures information from previous steps.
- **Transformers**: Use self-attention mechanisms to process sequences in parallel. They power modern language models like GPT and BERT.
