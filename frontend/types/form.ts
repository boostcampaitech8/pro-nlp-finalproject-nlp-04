export interface FormOption {
    label: string;
    value: string;
}

export interface FormSection {
    current_section: string;
    question: string;
    options: FormOption[];
    guide_text: string;
}

export interface FormRequest {
    message: string;
    forms: FormSection[];
}
