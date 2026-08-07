import os
import time
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

class PDFReportGenerator:
    def __init__(self, metrics_data):
        self.metrics = metrics_data

    def generate_confusion_matrix_plot(self, output_img_path):
        """Generates and saves a confusion matrix heatmap image using Matplotlib."""
        cm = self.metrics.get("confusion_matrix")
        classes = self.metrics.get("classes", [])
        
        plt.figure(figsize=(6, 5))
        plt.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
        plt.title('Confusion Matrix Heatmap', fontsize=12, fontweight='bold', pad=10)
        plt.colorbar()
        
        tick_marks = np.arange(len(classes))
        plt.xticks(tick_marks, classes, rotation=45, ha='right', fontsize=8)
        plt.yticks(tick_marks, classes, fontsize=8)

        # Draw values inside cells
        thresh = cm.max() / 2.0 if cm.max() > 0 else 1.0
        for i in range(cm.shape[0]):
            for j in range(cm.shape[1]):
                val = cm[i, j]
                plt.text(j, i, f"{val}",
                         horizontalalignment="center",
                         color="white" if val > thresh else "black",
                         fontsize=9, fontweight='bold')

        plt.tight_layout()
        plt.ylabel('True Class Label', fontsize=10, fontweight='bold')
        plt.xlabel('Predicted Class Label', fontsize=10, fontweight='bold')
        plt.savefig(output_img_path, dpi=200, bbox_inches='tight')
        plt.close()

    def generate_pdf(self, pdf_save_path):
        """Generates a professional PDF report containing evaluation metrics and confusion matrix in English."""
        os.makedirs(os.path.dirname(os.path.abspath(pdf_save_path)), exist_ok=True)
        
        # Temp image path for confusion matrix
        temp_cm_path = os.path.join(os.path.dirname(os.path.abspath(pdf_save_path)), "temp_cm.png")
        self.generate_confusion_matrix_plot(temp_cm_path)

        doc = SimpleDocTemplate(
            pdf_save_path,
            pagesize=letter,
            rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
        )

        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=22,
            textColor=colors.HexColor('#1E293B'),
            spaceAfter=6
        )

        subtitle_style = ParagraphStyle(
            'DocSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            textColor=colors.HexColor('#64748B'),
            spaceAfter=15
        )

        section_style = ParagraphStyle(
            'SectionTitle',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=13,
            textColor=colors.HexColor('#0F172A'),
            spaceBefore=12,
            spaceAfter=8
        )

        normal_style = ParagraphStyle(
            'BodyTextCustom',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor('#334155')
        )

        story = []

        # Document Header
        story.append(Paragraph("MEDIAPIPE GESTURE MODEL RELIABILITY REPORT", title_style))
        timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S")
        story.append(Paragraph(f"AI Drone Gesture Control Model Evaluation Report | Generated: {timestamp_str}", subtitle_style))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#3B82F6'), spaceAfter=15))

        # Model Quality Rating Box
        rating_grade = self.metrics.get("rating_grade", "N/A")
        rating_text = self.metrics.get("rating_text", "")
        rating_hex = self.metrics.get("rating_color", "#3B82F6")

        rating_table_data = [
            [
                Paragraph("<b>Overall Model Grade:</b>", ParagraphStyle('RL', parent=normal_style, fontSize=11, textColor=colors.HexColor('#1E293B'))),
                Paragraph(f"<b><font color='{rating_hex}' size=12>{rating_grade}</font></b>", normal_style)
            ],
            [
                Paragraph("<b>Evaluation Summary:</b>", normal_style),
                Paragraph(rating_text, normal_style)
            ]
        ]
        
        rating_table = Table(rating_table_data, colWidths=[2.0*inch, 5.2*inch])
        rating_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#E2E8F0')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#F1F5F9')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ]))
        story.append(rating_table)
        story.append(Spacer(1, 15))

        # Metrics Summary Table
        story.append(Paragraph("1. Key Performance Metrics Summary", section_style))
        
        acc = self.metrics.get("accuracy", 0.0) * 100.0
        prec = self.metrics.get("precision", 0.0) * 100.0
        rec = self.metrics.get("recall", 0.0) * 100.0
        f1 = self.metrics.get("f1_score", 0.0) * 100.0
        det_rate = self.metrics.get("detection_rate", 0.0)
        latency = self.metrics.get("avg_latency_ms", 0.0)
        fps = self.metrics.get("fps", 0.0)

        metrics_table_data = [
            ["Metric Name", "Value", "Metric Description"],
            ["Overall Accuracy", f"{acc:.2f}%", "Ratio of correctly predicted samples over total test samples"],
            ["Precision (Macro Avg)", f"{prec:.2f}%", "Average precision rate across all gesture classes"],
            ["Recall (Macro Avg)", f"{rec:.2f}%", "Average recall rate across all gesture classes"],
            ["F1-Score (Macro Avg)", f"{f1:.2f}%", "Harmonic mean of precision and recall"],
            ["Hand Detection Rate", f"{det_rate:.2f}%", "Percentage of test frames where hand landmarks were detected"],
            ["Inference Latency", f"{latency:.2f} ms", "Average processing latency per frame"],
            ["Processing Throughput", f"{fps:.1f} FPS", "Estimated processing frames per second"]
        ]

        metrics_table = Table(metrics_table_data, colWidths=[2.2*inch, 1.3*inch, 3.7*inch])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 9.5),
            ('BOTTOMPADDING', (0,0), (-1,0), 6),
            ('TOPPADDING', (0,0), (-1,0), 6),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
            ('ALIGN', (1,0), (1,-1), 'CENTER'),
        ]))
        story.append(metrics_table)
        story.append(Spacer(1, 15))

        # Dataset & Confusion Matrix Section
        story.append(Paragraph("2. Confusion Matrix & Test Dataset Overview", section_style))
        
        ds_info_text = f"<b>Total Test Samples:</b> {self.metrics.get('total_samples', 0)} | " \
                       f"<b>Hands Detected:</b> {self.metrics.get('detected_samples', 0)}<br/>" \
                       f"<b>Target Gesture Classes:</b> {', '.join(self.metrics.get('classes', []))}"
        story.append(Paragraph(ds_info_text, normal_style))
        story.append(Spacer(1, 10))

        if os.path.exists(temp_cm_path):
            img_cm = Image(temp_cm_path, width=4.5*inch, height=3.75*inch)
            story.append(img_cm)
            
        story.append(Spacer(1, 15))

        # Classification Report Details
        story.append(Paragraph("3. Per-Class Classification Report", section_style))
        clf_rep_str = self.metrics.get("classification_report", "")
        clf_rep_style = ParagraphStyle(
            'CodeStyle',
            parent=styles['Code'],
            fontName='Courier',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#0F172A')
        )
        clf_lines = clf_rep_str.split('\n')
        clf_formatted = "<br/>".join([line.replace(' ', '&nbsp;') for line in clf_lines])
        story.append(Paragraph(clf_formatted, clf_rep_style))

        # Build Document
        doc.build(story)

        # Clean up temp file
        if os.path.exists(temp_cm_path):
            try:
                os.remove(temp_cm_path)
            except Exception:
                pass

        return True, "PDF report generated successfully in English."
