import os
import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ReportLab Imports
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

class ReportGenerator:
    def __init__(self, results, best_model_name, dataset_stats, training_settings):
        self.results = results
        self.best_model_name = best_model_name
        self.dataset_stats = dataset_stats
        self.training_settings = training_settings

    def generate_pdf_report(self, output_path):
        """
        Generates a professional PDF report containing the dataset analysis,
        model comparison results, training configuration, and detailed metrics of the best model.
        """
        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            
            doc = SimpleDocTemplate(
                output_path,
                pagesize=letter,
                rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54
            )
            
            styles = getSampleStyleSheet()
            
            # Custom Styles
            title_style = ParagraphStyle(
                'DocTitle',
                parent=styles['Heading1'],
                fontName='Helvetica-Bold',
                fontSize=24,
                textColor=colors.HexColor('#002B49'),
                spaceAfter=15
            )
            
            subtitle_style = ParagraphStyle(
                'DocSubtitle',
                parent=styles['Normal'],
                fontName='Helvetica',
                fontSize=12,
                textColor=colors.HexColor('#555555'),
                spaceAfter=25
            )

            h1_style = ParagraphStyle(
                'H1Style',
                parent=styles['Heading2'],
                fontName='Helvetica-Bold',
                fontSize=16,
                textColor=colors.HexColor('#002B49'),
                spaceBefore=15,
                spaceAfter=10
            )

            h2_style = ParagraphStyle(
                'H2Style',
                parent=styles['Heading3'],
                fontName='Helvetica-Bold',
                fontSize=12,
                textColor=colors.HexColor('#128C7E'),
                spaceBefore=10,
                spaceAfter=5
            )

            body_style = ParagraphStyle(
                'BodyStyle',
                parent=styles['Normal'],
                fontName='Helvetica',
                fontSize=10,
                textColor=colors.HexColor('#333333'),
                leading=14,
                spaceAfter=8
            )

            code_style = ParagraphStyle(
                'CodeStyle',
                parent=styles['Code'],
                fontName='Courier',
                fontSize=8,
                textColor=colors.HexColor('#222222'),
                leading=10,
                backColor=colors.HexColor('#F4F4F4'),
                borderColor=colors.HexColor('#DDDDDD'),
                borderWidth=1,
                borderPadding=5,
                spaceAfter=10
            )

            story = []

            # Document Header
            story.append(Paragraph("AI Gesture Model Trainer Report", title_style))
            story.append(Paragraph(f"Project: Hand Gesture Drone Control System | Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}", subtitle_style))
            story.append(Spacer(1, 10))

            # 1. Dataset Analysis Summary
            story.append(Paragraph("1. Dataset Summary", h1_style))
            dataset_table_data = [
                [Paragraph("<b>Metric</b>", body_style), Paragraph("<b>Value</b>", body_style)],
                [Paragraph("Dataset Path", body_style), Paragraph(str(self.dataset_stats.get("file_path")), body_style)],
                [Paragraph("Total Sample Count", body_style), Paragraph(str(self.dataset_stats.get("samples_count")), body_style)],
                [Paragraph("Feature Columns (Coordinates)", body_style), Paragraph(str(self.dataset_stats.get("features_count")), body_style)],
                [Paragraph("Number of Gesture Classes", body_style), Paragraph(str(self.dataset_stats.get("classes_count")), body_style)],
                [Paragraph("Missing / NaN Values", body_style), Paragraph(str(self.dataset_stats.get("nan_count")), body_style)]
            ]
            
            t_dataset = Table(dataset_table_data, colWidths=[200, 300])
            t_dataset.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F2F5F8')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#002B49')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
            ]))
            story.append(t_dataset)
            story.append(Spacer(1, 15))

            # 2. Training Configuration
            story.append(Paragraph("2. Training Settings", h1_style))
            settings_table_data = [
                [Paragraph("<b>Parameter</b>", body_style), Paragraph("<b>Value</b>", body_style)],
                [Paragraph("Train / Test Ratio", body_style), Paragraph(self.training_settings.get("ratio", "80/20"), body_style)],
                [Paragraph("Random State Seed", body_style), Paragraph(str(self.training_settings.get("seed", 42)), body_style)],
                [Paragraph("Cross Validation", body_style), Paragraph(f"{self.training_settings.get('cv_folds', 5)} Folds", body_style)],
                [Paragraph("Normalize Features", body_style), Paragraph("Yes (StandardScaler)" if self.training_settings.get("normalize") else "No", body_style)],
                [Paragraph("Shuffle Dataset", body_style), Paragraph("Yes" if self.training_settings.get("shuffle") else "No", body_style)]
            ]
            t_settings = Table(settings_table_data, colWidths=[200, 300])
            t_settings.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F2F5F8')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#002B49')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
            ]))
            story.append(t_settings)
            story.append(Spacer(1, 20))

            # Page Break for clean structure
            story.append(PageBreak())

            # 3. Model Comparison
            story.append(Paragraph("3. Model Performance Comparison", h1_style))
            
            # Header Row
            comp_table_data = [
                ["Model", "Accuracy", "Precision", "Recall", "F1", "Train Time", "Mem Size"]
            ]
            # Fill rows
            for m_name, res in self.results.items():
                comp_table_data.append([
                    m_name,
                    f"{res['accuracy']*100:.2f}%",
                    f"{res['precision']*100:.2f}%",
                    f"{res['recall']*100:.2f}%",
                    f"{res['f1']*100:.2f}%",
                    f"{res['train_time']:.4f}s",
                    f"{res['memory_usage']:.1f} KB"
                ])
                
            t_comp = Table(comp_table_data, colWidths=[120, 60, 60, 60, 60, 70, 70])
            t_comp.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#002B49')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9F9F9')]),
            ]))
            story.append(t_comp)
            story.append(Spacer(1, 20))

            # Save comparison chart temporarily and embed
            temp_chart_path = "temp_pdf_chart.png"
            self._save_comparison_chart_image(temp_chart_path)
            if os.path.exists(temp_chart_path):
                img = Image(temp_chart_path, width=6.5*inch, height=3.5*inch)
                story.append(img)
                story.append(Spacer(1, 15))
            
            # 4. Best Model Breakdown
            story.append(PageBreak())
            story.append(Paragraph(f"4. Selected Best Model Details: {self.best_model_name}", h1_style))
            
            best_res = self.results[self.best_model_name]
            
            best_model_data = [
                [Paragraph("<b>Metric</b>", body_style), Paragraph("<b>Result Score</b>", body_style)],
                [Paragraph("Accuracy Score", body_style), Paragraph(f"<b>{best_res['accuracy']*100:.4f}%</b>", body_style)],
                [Paragraph("Precision (Macro)", body_style), Paragraph(f"{best_res['precision']*100:.4f}%", body_style)],
                [Paragraph("Recall (Macro)", body_style), Paragraph(f"{best_res['recall']*100:.4f}%", body_style)],
                [Paragraph("F1 Score (Macro)", body_style), Paragraph(f"{best_res['f1']*100:.4f}%", body_style)],
                [Paragraph("Single Sample Latency", body_style), Paragraph(f"{best_res['single_pred_time']*1000:.4f} ms", body_style)],
                [Paragraph("Model Serialization Size", body_style), Paragraph(f"{best_res['memory_usage']:.2f} KB", body_style)]
            ]
            t_best = Table(best_model_data, colWidths=[200, 300])
            t_best.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E8F5E9')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#2E7D32')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
            ]))
            story.append(t_best)
            story.append(Spacer(1, 15))

            # Classification report code block
            story.append(Paragraph("Classification Report Detail:", h2_style))
            story.append(Paragraph(best_res["classification_report"].replace("\n", "<br/>").replace(" ", "&nbsp;"), code_style))

            # Build PDF
            doc.build(story)
            
            # Clean up temp image
            if os.path.exists(temp_chart_path):
                os.remove(temp_chart_path)
                
            return True, "PDF training report generated successfully."
        except Exception as e:
            return False, f"Failed to generate PDF: {str(e)}"

    def export_csv_results(self, output_path):
        """
        Exports a CSV with all metrics for all models.
        """
        try:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            rows = []
            for name, res in self.results.items():
                rows.append({
                    "Model": name,
                    "Accuracy": res["accuracy"],
                    "Precision": res["precision"],
                    "Recall": res["recall"],
                    "F1_Score": res["f1"],
                    "Training_Time_Sec": res["train_time"],
                    "Prediction_Time_Sec": res["pred_time"],
                    "Single_Latency_Sec": res["single_pred_time"],
                    "Memory_Usage_KB": res["memory_usage"]
                })
            df = pd.DataFrame(rows)
            df.to_csv(output_path, index=False)
            return True, "CSV results exported successfully."
        except Exception as e:
            return False, f"Failed to export CSV: {str(e)}"

    def export_comparison_csv(self, output_path):
        """
        Exports model comparison CSV.
        """
        return self.export_csv_results(output_path)

    def export_log(self, output_path, log_content):
        """
        Saves the UI training log string to a text file.
        """
        try:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(log_content)
            return True, "Training logs exported successfully."
        except Exception as e:
            return False, f"Failed to export log: {str(e)}"

    def _save_comparison_chart_image(self, path):
        """
        Generates and saves a clean, white-background comparison chart image
        for embedding in the PDF.
        """
        try:
            # Create a small, clean graph for the PDF
            fig, ax = plt.subplots(figsize=(7, 3.5))
            
            models = list(self.results.keys())
            accuracies = [self.results[m]["accuracy"] * 100 for m in models]
            f1s = [self.results[m]["f1"] * 100 for m in models]
            
            x = np.arange(len(models))
            width = 0.35
            
            rects1 = ax.bar(x - width/2, accuracies, width, label='Accuracy', color='#128C7E')
            rects2 = ax.bar(x + width/2, f1s, width, label='F1 Score', color='#002B49')
            
            ax.set_ylabel('Percentage (%)', fontsize=9)
            ax.set_title('Accuracy and F1 Score Comparison', fontsize=11, fontweight='bold')
            ax.set_xticks(x)
            ax.set_xticklabels(models, rotation=10, ha='right', fontsize=8)
            ax.legend(fontsize=8)
            ax.set_ylim(0, 110)
            
            for rect in rects1:
                height = rect.get_height()
                ax.annotate(f'{height:.1f}%',
                            xy=(rect.get_x() + rect.get_width() / 2, height),
                            xytext=(0, 2), textcoords="offset points",
                            ha='center', va='bottom', fontsize=7)
                            
            for rect in rects2:
                height = rect.get_height()
                ax.annotate(f'{height:.1f}%',
                            xy=(rect.get_x() + rect.get_width() / 2, height),
                            xytext=(0, 2), textcoords="offset points",
                            ha='center', va='bottom', fontsize=7)
            
            plt.tight_layout()
            plt.savefig(path, dpi=200)
            plt.close(fig)
        except Exception:
            pass
