"""
Test and demonstration of the LaTeX processor capabilities.

This module provides comprehensive tests for the LaTeX processor,
demonstrating its ability to handle various LaTeX constructs and
academic document features.
"""

import asyncio
import tempfile
import os
from pathlib import Path
from uuid import uuid4

from app.services.document_processing.processors.latex_processor import LaTeXProcessor
from app.domain.schemas.document_processing import (
    ProcessingRequest,
    DocumentType
)


# Sample LaTeX document for testing
SAMPLE_LATEX_DOCUMENT = r"""
\documentclass[12pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[english]{babel}
\usepackage{amsmath,amssymb,amsthm}
\usepackage{graphicx}
\usepackage{cite}
\usepackage{url}

\title{Advanced Mathematical Analysis in Quantum Computing}
\author{Dr. Alice Johnson\and Prof. Bob Smith\and Dr. Carol Williams}
\date{\today}

\newtheorem{theorem}{Theorem}
\newtheorem{lemma}{Lemma}
\newtheorem{definition}{Definition}

\begin{document}

\maketitle

\begin{abstract}
This paper presents a comprehensive analysis of mathematical frameworks used in quantum computing. We introduce novel approaches to quantum state representation and demonstrate their effectiveness through rigorous mathematical proofs. Our results show significant improvements in computational efficiency for specific quantum algorithms.
\end{abstract}

\section{Introduction}

Quantum computing represents a paradigm shift in computational theory. The fundamental principles rely on quantum mechanical phenomena such as superposition and entanglement. As shown in \cite{nielsen2010quantum}, these properties enable exponential speedups for certain computational problems.

The quantum state of an $n$-qubit system can be represented as:
\begin{equation}
|\psi\rangle = \sum_{i=0}^{2^n-1} \alpha_i |i\rangle
\label{eq:quantum_state}
\end{equation}
where $\alpha_i$ are complex amplitudes satisfying $\sum_{i=0}^{2^n-1} |\alpha_i|^2 = 1$.

\section{Mathematical Framework}

\subsection{Quantum State Representation}

Let us define the Hilbert space $\mathcal{H}$ for our quantum system. The dimension of this space grows exponentially with the number of qubits.

\begin{definition}
A quantum state $|\psi\rangle$ is a unit vector in the Hilbert space $\mathcal{H}$, i.e., $\langle\psi|\psi\rangle = 1$.
\end{definition}

\begin{theorem}
For any unitary operator $U$ acting on $\mathcal{H}$, the evolved state $U|\psi\rangle$ remains normalized.
\label{thm:unitary_evolution}
\end{theorem}

\begin{proof}
Since $U$ is unitary, we have $U^\dagger U = I$. Therefore:
\begin{align}
\langle U\psi | U\psi \rangle &= \langle \psi | U^\dagger U | \psi \rangle \\
&= \langle \psi | I | \psi \rangle \\
&= \langle \psi | \psi \rangle = 1
\end{align}
This completes the proof.
\end{proof}

\subsection{Quantum Gates and Circuits}

The most fundamental single-qubit gates include:
\begin{itemize}
\item Pauli-X gate: $X = \begin{pmatrix} 0 & 1 \\ 1 & 0 \end{pmatrix}$
\item Pauli-Y gate: $Y = \begin{pmatrix} 0 & -i \\ i & 0 \end{pmatrix}$
\item Pauli-Z gate: $Z = \begin{pmatrix} 1 & 0 \\ 0 & -1 \end{pmatrix}$
\item Hadamard gate: $H = \frac{1}{\sqrt{2}}\begin{pmatrix} 1 & 1 \\ 1 & -1 \end{pmatrix}$
\end{itemize}

The action of the Hadamard gate on computational basis states is given by:
$$H|0\rangle = \frac{|0\rangle + |1\rangle}{\sqrt{2}}, \quad H|1\rangle = \frac{|0\rangle - |1\rangle}{\sqrt{2}}$$

\section{Advanced Topics}

\subsection{Quantum Error Correction}

Quantum error correction is essential for fault-tolerant quantum computation. The quantum error correction condition \citep{gottesman1997stabilizer} states that a quantum error correcting code can correct errors $E_i$ if and only if:
\begin{equation}
\langle \psi_j | E_i^\dagger E_k | \psi_l \rangle = C_{ik} \delta_{jl}
\label{eq:qec_condition}
\end{equation}
for some Hermitian matrix $C$.

\begin{figure}[h]
\centering
\includegraphics[width=0.8\textwidth]{quantum_circuit_diagram.png}
\caption{Quantum circuit diagram showing a typical quantum error correction scheme with syndrome extraction and recovery operations.}
\label{fig:qec_circuit}
\end{figure}

\subsection{Quantum Algorithms}

Several quantum algorithms demonstrate exponential speedups:

\begin{table}[h]
\centering
\begin{tabular}{|l|c|c|}
\hline
Algorithm & Classical Complexity & Quantum Complexity \\
\hline
Factoring & $O(e^{n^{1/3}})$ & $O(n^3)$ \\
Database Search & $O(n)$ & $O(\sqrt{n})$ \\
Simulation & $O(2^n)$ & $O(n^k)$ \\
\hline
\end{tabular}
\caption{Comparison of classical and quantum algorithmic complexities}
\label{tab:complexity_comparison}
\end{table}

As shown in Table~\ref{tab:complexity_comparison}, quantum algorithms can provide significant computational advantages.

\section{Results and Discussion}

Our theoretical analysis in Section~\ref{sec:mathematical_framework} provides the foundation for understanding quantum computational advantages. The unitary evolution theorem (Theorem~\ref{thm:unitary_evolution}) ensures that quantum states remain properly normalized throughout computation.

The quantum state representation in Equation~\ref{eq:quantum_state} allows us to track the evolution of complex quantum systems. Combined with the error correction condition (Equation~\ref{eq:qec_condition}), we can design robust quantum algorithms.

\section{Conclusion}

This work presents a mathematical framework for quantum computing that addresses both theoretical foundations and practical implementations. Future work will focus on extending these results to noisy intermediate-scale quantum (NISQ) devices.

\section*{Acknowledgments}

We thank the Quantum Computing Research Group for valuable discussions and feedback.

\bibliography{quantum_computing}
\bibliographystyle{plain}

\end{document}
"""

# Sample bibliography file
SAMPLE_BIBLIOGRAPHY = r"""
@book{nielsen2010quantum,
  title={Quantum computation and quantum information},
  author={Nielsen, Michael A and Chuang, Isaac L},
  year={2010},
  publisher={Cambridge University Press},
  edition={10th Anniversary},
  pages={676},
  isbn={978-1107002173}
}

@article{gottesman1997stabilizer,
  title={Stabilizer codes and quantum error correction},
  author={Gottesman, Daniel},
  journal={arXiv preprint quant-ph/9705052},
  year={1997},
  url={https://arxiv.org/abs/quant-ph/9705052}
}

@inproceedings{shor1994algorithms,
  title={Algorithms for quantum computation: discrete logarithms and factoring},
  author={Shor, Peter W},
  booktitle={Proceedings 35th annual symposium on foundations of computer science},
  pages={124--134},
  year={1994},
  organization={IEEE},
  doi={10.1109/SFCS.1994.365700}
}

@article{grover1996fast,
  title={A fast quantum mechanical algorithm for database search},
  author={Grover, Lov K},
  journal={Proceedings of the twenty-eighth annual ACM symposium on Theory of computing},
  pages={212--219},
  year={1996},
  doi={10.1145/237814.237866}
}

@article{preskill2018quantum,
  title={Quantum computing in the NISQ era and beyond},
  author={Preskill, John},
  journal={Quantum},
  volume={2},
  pages={79},
  year={2018},
  publisher={Verein zur F{\"o}rderung des Open Access Publizierens in den Quantenwissenschaften},
  doi={10.22331/q-2018-08-06-79}
}
"""


async def test_latex_processor():
    """Test the LaTeX processor with a comprehensive academic document."""
    
    print("Testing LaTeX Processor")
    print("=" * 50)
    
    # Create temporary files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Write LaTeX file
        latex_file = temp_path / "test_document.tex"
        with open(latex_file, 'w', encoding='utf-8') as f:
            f.write(SAMPLE_LATEX_DOCUMENT)
        
        # Write bibliography file
        bib_file = temp_path / "quantum_computing.bib"
        with open(bib_file, 'w', encoding='utf-8') as f:
            f.write(SAMPLE_BIBLIOGRAPHY)
        
        # Initialize processor
        processor = LaTeXProcessor()
        
        # Test document validation
        print("1. Testing document validation...")
        try:
            is_valid = await processor.validate_document(latex_file)
            print(f"   Document validation: {'PASS' if is_valid else 'FAIL'}")
        except Exception as e:
            print(f"   Document validation failed: {e}")
            return
        
        # Test processing capabilities
        print("\n2. Testing processor capabilities...")
        capabilities = processor.capabilities
        for cap_name, capability in capabilities.items():
            status = "SUPPORTED" if capability.supported else "NOT SUPPORTED"
            print(f"   {capability.name}: {status} (confidence: {capability.confidence:.2f})")
        
        # Test full document processing
        print("\n3. Testing full document processing...")
        
        request = ProcessingRequest(
            document_id=uuid4(),
            file_path=str(latex_file),
            document_type=DocumentType.LATEX,
            extract_text=True,
            extract_figures=True,
            extract_tables=True,
            extract_citations=True,
            extract_references=True,
            extract_metadata=True,
            preserve_layout=True
        )
        
        try:
            result = await processor.process(request)
            
            print(f"   Processing status: {result.status.value}")
            
            if result.status.value == "completed":
                print(f"\n4. Processing Results:")
                print(f"   Document title: {result.metadata.title}")
                print(f"   Authors: {', '.join(result.metadata.authors)}")
                print(f"   Document type: {result.metadata.document_type}")
                print(f"   Abstract length: {len(result.metadata.abstract or '')} characters")
                
                print(f"\n   Document Structure:")
                print(f"   - Sections: {len(result.sections)}")
                for i, section in enumerate(result.sections[:5]):  # Show first 5 sections
                    print(f"     {i+1}. {section.title} (Level {section.level})")
                
                print(f"\n   Content Elements:")
                print(f"   - Total elements: {len(result.elements)}")
                print(f"   - Figures: {len(result.figures)}")
                print(f"   - Tables: {len(result.tables)}")
                print(f"   - Citations: {len(result.citations)}")
                print(f"   - References: {len(result.references)}")
                
                # Show element types breakdown
                element_types = {}
                for element in result.elements:
                    elem_type = element.element_type
                    element_types[elem_type] = element_types.get(elem_type, 0) + 1
                
                print(f"\n   Element Type Breakdown:")
                for elem_type, count in element_types.items():
                    print(f"   - {elem_type}: {count}")
                
                # Show some example elements
                print(f"\n   Sample Elements:")
                
                # Show equations
                equations = [e for e in result.elements if e.element_type in ['equation', 'math_inline']]
                if equations:
                    print(f"   Sample Equation: {equations[0].content[:100]}...")
                
                # Show citations
                if result.citations:
                    print(f"   Sample Citation: {result.citations[0].content}")
                
                # Show references
                if result.references:
                    ref = result.references[0]
                    print(f"   Sample Reference: {ref.authors[0] if ref.authors else 'Unknown'} - {ref.title[:50]}...")
                
                print(f"\n   Metadata Analysis:")
                if result.metadata.keywords:
                    print(f"   - Keywords: {', '.join(result.metadata.keywords)}")
                print(f"   - Language: {result.metadata.language}")
                
            else:
                print(f"   Processing failed: {result.error_message}")
                
        except Exception as e:
            print(f"   Processing failed with exception: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n5. Testing individual components...")
        
        # Test tokenizer
        try:
            from app.services.document_processing.utils.latex_parser import LaTeXTokenizer
            tokenizer = LaTeXTokenizer()
            tokens = tokenizer.tokenize(SAMPLE_LATEX_DOCUMENT[:500])  # First 500 chars
            print(f"   Tokenizer: Generated {len(tokens)} tokens")
        except Exception as e:
            print(f"   Tokenizer test failed: {e}")
        
        # Test equation renderer
        try:
            from app.services.document_processing.utils.equation_renderer import EquationRenderer
            renderer = EquationRenderer()
            test_eq = r"\sum_{i=0}^{n} \alpha_i |i\rangle"
            rendered = renderer.render_equation(test_eq, formats=['plain_text'])
            print(f"   Equation Renderer: Rendered equation to plain text: {rendered.plain_text}")
        except Exception as e:
            print(f"   Equation renderer test failed: {e}")
        
        # Test bibliography parser
        try:
            from app.services.document_processing.utils.citation_manager import BibTeXParser
            bib_parser = BibTeXParser()
            entries = bib_parser.parse_string(SAMPLE_BIBLIOGRAPHY)
            print(f"   Bibliography Parser: Parsed {len(entries)} entries")
            if entries:
                first_entry = list(entries.values())[0]
                print(f"     First entry: {first_entry.title[:50]}...")
        except Exception as e:
            print(f"   Bibliography parser test failed: {e}")
    
    print("\nLaTeX Processor Testing Complete!")


async def demonstrate_advanced_features():
    """Demonstrate advanced LaTeX processing features."""
    
    print("\nAdvanced LaTeX Processing Features")
    print("=" * 50)
    
    # Complex math example
    complex_math = r"""
    \begin{align}
    \nabla \times \mathbf{E} &= -\frac{\partial \mathbf{B}}{\partial t} \label{eq:faraday} \\
    \nabla \times \mathbf{B} &= \mu_0 \mathbf{J} + \mu_0 \epsilon_0 \frac{\partial \mathbf{E}}{\partial t} \label{eq:ampere}
    \end{align}
    """
    
    # Test equation parsing
    try:
        from app.services.document_processing.utils.equation_renderer import EquationParser
        parser = EquationParser()
        info = parser.parse_equation(complex_math, "align")
        
        print("1. Complex Equation Analysis:")
        print(f"   Variables found: {info.variables}")
        print(f"   Functions found: {info.functions}")
        print(f"   Operators found: {info.operators}")
        print(f"   Complexity score: {info.complexity_score:.2f}")
        print(f"   Has fractions: {info.has_fractions}")
        print(f"   Has integrals: {info.has_integrals}")
        print(f"   Has summations: {info.has_summations}")
        
    except Exception as e:
        print(f"   Equation analysis failed: {e}")
    
    # Test citation extraction
    citation_text = r"""
    Recent advances in quantum computing \cite{nielsen2010quantum,preskill2018quantum} 
    have shown promising results. As demonstrated by \citet{shor1994algorithms}, 
    quantum algorithms can achieve exponential speedups for specific problems.
    """
    
    try:
        from app.services.document_processing.utils.citation_manager import CitationExtractor
        extractor = CitationExtractor()
        citations = extractor.extract_citations(citation_text)
        
        print("\n2. Citation Extraction:")
        print(f"   Found {len(citations)} citations")
        for citation in citations:
            print(f"   - Type: {citation.citation_type.value}, Key: {citation.citation_key}")
            if citation.multiple_keys:
                print(f"     Multiple keys: {citation.multiple_keys}")
        
    except Exception as e:
        print(f"   Citation extraction failed: {e}")
    
    # Test cross-reference resolution
    ref_text = r"""
    As shown in Equation~\ref{eq:quantum_state}, the quantum state can be written as a superposition.
    See also Theorem~\ref{thm:unitary_evolution} and Figure~\ref{fig:qec_circuit}.
    """
    
    try:
        from app.services.document_processing.utils.latex_parser import LaTeXTokenizer, LaTeXParser
        tokenizer = LaTeXTokenizer()
        tokens = tokenizer.tokenize(ref_text)
        parser = LaTeXParser(tokens)
        commands, _ = parser.parse()
        
        ref_commands = [cmd for cmd in commands if cmd.name in ['ref', 'eqref']]
        print(f"\n3. Cross-reference Detection:")
        print(f"   Found {len(ref_commands)} references")
        for cmd in ref_commands:
            if cmd.arguments:
                print(f"   - Reference to: {cmd.arguments[0]}")
        
    except Exception as e:
        print(f"   Cross-reference detection failed: {e}")


if __name__ == "__main__":
    # Run the tests
    asyncio.run(test_latex_processor())
    asyncio.run(demonstrate_advanced_features())