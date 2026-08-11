import os
import time
import psutil
import numpy as np

class EvaluatorEngine:
    def __init__(self, input_shape=(1, 63)):
        self.input_shape = input_shape
        self.supported_extensions = ['.pkl', '.joblib', '.onnx', '.pt', '.pth', '.tflite']

    def evaluate(self, model_path, num_iterations=1000):
        results = {
            "model_path": model_path,
            "model_name": os.path.basename(model_path),
            "model_size_kb": 0,
            "latency_ms": 0,
            "fps": 0,
            "throughput": 0,
            "cpu_percent": 0,
            "ram_usage_mb": 0,
            "error": None
        }
        
        if not os.path.exists(model_path):
            results["error"] = f"File {model_path} not found."
            return results

        results["model_size_kb"] = os.path.getsize(model_path) / 1024.0
        ext = os.path.splitext(model_path)[1].lower()
        
        if ext not in self.supported_extensions:
            results["error"] = f"Unsupported extension: {ext}"
            return results

        dummy_input = np.random.rand(*self.input_shape).astype(np.float32)
        predict_func = None

        try:
            if ext in ['.pkl', '.joblib']:
                import joblib
                model = joblib.load(model_path)
                predict_func = lambda x: model.predict(x)
                
            elif ext == '.onnx':
                import onnxruntime as ort
                session = ort.InferenceSession(model_path)
                input_name = session.get_inputs()[0].name
                predict_func = lambda x: session.run(None, {input_name: x})
                
            elif ext in ['.pt', '.pth']:
                import torch
                model = torch.load(model_path, map_location=torch.device('cpu'))
                model.eval()
                dummy_input_tensor = torch.tensor(dummy_input)
                predict_func = lambda x: model(dummy_input_tensor)
                
            elif ext == '.tflite':
                import tensorflow as tf
                interpreter = tf.lite.Interpreter(model_path=model_path)
                interpreter.allocate_tensors()
                input_details = interpreter.get_input_details()
                output_details = interpreter.get_output_details()
                def tflite_pred(x):
                    interpreter.set_tensor(input_details[0]['index'], x)
                    interpreter.invoke()
                    return interpreter.get_tensor(output_details[0]['index'])
                predict_func = tflite_pred
                
        except Exception as e:
            results["error"] = f"Loading error: {str(e)}"
            return results

        # Warmup
        try:
            for _ in range(10):
                predict_func(dummy_input)
        except Exception as e:
            results["error"] = f"Inference error during warmup: {str(e)}"
            return results
            
        # Benchmark
        start_time = time.time()
        for _ in range(num_iterations):
            predict_func(dummy_input)
        end_time = time.time()
        
        total_time = end_time - start_time
        avg_latency = total_time / num_iterations
        fps = 1.0 / avg_latency if avg_latency > 0 else 0
        throughput = fps * self.input_shape[0]
        
        results["latency_ms"] = avg_latency * 1000
        results["fps"] = fps
        results["throughput"] = throughput
        
        process = psutil.Process(os.getpid())
        results["cpu_percent"] = process.cpu_percent(interval=1.0)
        results["ram_usage_mb"] = process.memory_info().rss / (1024 * 1024)
        
        return results
