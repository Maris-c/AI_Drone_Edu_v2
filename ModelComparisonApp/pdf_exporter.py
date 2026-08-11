import os
import time
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

class PDFExporter:
    def __init__(self, results_list):
        self.results_list = results_list

    def _generate_bar_chart(self, title, metric_key, ylabel, output_path, color='#3B82F6'):
        models = [res["model_name"] for res in self.results_list]
        values = [res[metric_key] for res in self.results_list]
        
        plt.figure(figsize=(6, 4))
        bars = plt.bar(models, values, color=color)
        plt.title(title, fontsize=12, fontweight='bold', pad=15)
        plt.ylabel(ylabel, fontsize=10, fontweight='bold')
        
        plt.xticks(rotation=15, ha='right', fontsize=9)
        plt.tight_layout()
        
        for bar in bars:
            yval = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2, yval + (max(values)*0.01 if max(values) > 0 else 0),
                     f"{yval:.2f}", ha='center', va='bottom', fontsize=9, fontweight='bold')
            
        plt.savefig(output_path, dpi=200, bbox_inches='tight')
        plt.close()

    def generate_pdf(self, pdf_save_path):
        os.makedirs(os.path.dirname(os.path.abspath(pdf_save_path)), exist_ok=True)
        
        # Temp images
        temp_dir = os.path.dirname(os.path.abspath(pdf_save_path))
        latency_img = os.path.join(temp_dir, "temp_latency.png")
        fps_img = os.path.join(temp_dir, "temp_fps.png")
        size_img = os.path.join(temp_dir, "temp_size.png")
        
        self._generate_bar_chart("Model Latency Comparison (Lower is Better)", "latency_ms", "Latency (ms)", latency_img, color='#EF4444')
        self._generate_bar_chart("Model FPS Comparison (Higher is Better)", "fps", "Frames Per Second", fps_img, color='#10B981')
        self._generate_bar_chart("Model Size Comparison (Lower is Better)", "model_size_kb", "Size (KB)", size_img, color='#F59E0B')

        doc = SimpleDocTemplate(
            pdf_save_path,
            pagesize=letter,
            rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=22, textColor=colors.HexColor('#1E293B'), spaceAfter=6)
        subtitle_style = ParagraphStyle('DocSubtitle', parent=styles['Normal'], fontName='Helvetica', fontSize=10, textColor=colors.HexColor('#64748B'), spaceAfter=15)
        section_style = ParagraphStyle('SectionTitle', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=13, textColor=colors.HexColor('#0F172A'), spaceBefore=12, spaceAfter=8)
        normal_style = ParagraphStyle('BodyTextCustom', parent=styles['Normal'], fontName='Helvetica', fontSize=9.5, leading=13, textColor=colors.HexColor('#334155'))

        story = []

        # Header
        story.append(Paragraph("AI DRONE - MODEL EVALUATION & COMPARISON REPORT", title_style))
        story.append(Paragraph(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}", subtitle_style))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#3B82F6'), spaceAfter=15))

        # Overview Table
        story.append(Paragraph("1. Performance Metrics Overview", section_style))
        
        table_data = [["Model Name", "Latency (ms)", "FPS", "Throughput", "Size (KB)", "RAM (MB)"]]
        for res in self.results_list:
            table_data.append([
                res["model_name"][:20] + ("..." if len(res["model_name"]) > 20 else ""),
                f"{res['latency_ms']:.3f}",
                f"{res['fps']:.1f}",
                f"{res['throughput']:.1f}",
                f"{res['model_size_kb']:.2f}",
                f"{res['ram_usage_mb']:.1f}"
            ])
            
        table = Table(table_data, colWidths=[2.2*inch, 1.0*inch, 1.0*inch, 1.0*inch, 1.0*inch, 1.0*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 9.5),
            ('BOTTOMPADDING', (0,0), (-1,0), 6),
            ('TOPPADDING', (0,0), (-1,0), 6),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
            ('ALIGN', (1,0), (-1,-1), 'CENTER'),
            ('ALIGN', (0,1), (0,-1), 'LEFT'),
        ]))
        story.append(table)
        story.append(Spacer(1, 15))

        # Charts
        story.append(Paragraph("2. Visual Comparisons", section_style))
        
        if os.path.exists(latency_img):
            story.append(Image(latency_img, width=5.5*inch, height=3.6*inch))
            story.append(Spacer(1, 10))
            
        if os.path.exists(fps_img):
            story.append(Image(fps_img, width=5.5*inch, height=3.6*inch))
            story.append(Spacer(1, 10))
            
        if os.path.exists(size_img):
            story.append(Image(size_img, width=5.5*inch, height=3.6*inch))

        doc.build(story)

        # Cleanup
        for img in [latency_img, fps_img, size_img]:
            if os.path.exists(img):
                os.remove(img)
                
        return True, "PDF exported successfully."
