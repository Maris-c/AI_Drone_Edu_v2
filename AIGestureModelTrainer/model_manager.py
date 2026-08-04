import os
import joblib

class ModelManager:
    @staticmethod
    def save_best_model(model_dir, best_model_name, results):
        """
        Saves the best model and optional scaler to the specified directory.
        Best model is saved as "gesture_model.pkl"
        Scaler (if applicable) is saved as "scaler.pkl"
        """
        try:
            os.makedirs(model_dir, exist_ok=True)
            
            best_res = results.get(best_model_name)
            if not best_res:
                return False, "Model results not found."
                
            model_obj = best_res.get("model_object")
            scaler_obj = best_res.get("scaler_object")
            
            # Save Model
            model_path = os.path.join(model_dir, "gesture_model.pkl")
            joblib.dump(model_obj, model_path)
            
            # Save Scaler if present
            scaler_path = os.path.join(model_dir, "scaler.pkl")
            if scaler_obj is not None:
                joblib.dump(scaler_obj, scaler_path)
                message = f"Saved best model ({best_model_name}) and its scaler to '{model_dir}' successfully."
            else:
                # If scaler already exists from a previous run, delete it so we don't mix them up
                if os.path.exists(scaler_path):
                    try:
                        os.remove(scaler_path)
                    except OSError:
                        pass
                message = f"Saved best model ({best_model_name}) without scaler (not required) to '{model_dir}' successfully."
                
            return True, message
        except Exception as e:
            return False, f"Failed to save model: {str(e)}"

    @staticmethod
    def load_model(model_dir):
        """
        Loads the saved model and scaler from the specified directory.
        Returns a tuple: (model, scaler)
        """
        model_path = os.path.join(model_dir, "gesture_model.pkl")
        scaler_path = os.path.join(model_dir, "scaler.pkl")
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found at {model_path}")
            
        model = joblib.load(model_path)
        scaler = joblib.load(scaler_path) if os.path.exists(scaler_path) else None
        
        return model, scaler
