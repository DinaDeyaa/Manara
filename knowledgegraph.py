from __future__ import annotations

from pathlib import Path
import json
import re
from rdflib import Graph, Namespace, RDF, RDFS, OWL, Literal, URIRef


# =========================================================
# CONFIG
# =========================================================

PROJECT_DIR = Path("/Users/dinaal-memah/Desktop/graduation project 2")
COURSES_DIR = PROJECT_DIR / "courses"
OUTPUT_FILE = PROJECT_DIR / "course_knowledge_graph.ttl"

BASE_URI = "http://manara.org/kg/"
EX = Namespace(BASE_URI)
MANARA = Namespace(BASE_URI + "ontology/")


# =========================================================
# HELPERS
# =========================================================

def safe_id(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", text.strip().lower()).strip("_")


def load_json_file(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_course_folders(courses_dir: Path) -> list[Path]:
    return sorted([p for p in courses_dir.iterdir() if p.is_dir()])


def make_uri(entity_type: str, identifier: str) -> URIRef:
    return EX[f"{entity_type}/{safe_id(identifier)}"]


# =========================================================
# RDF SCHEMA
# =========================================================

def add_schema(g: Graph):
    g.bind("ex", EX)
    g.bind("manara", MANARA)
    g.bind("rdf", RDF)
    g.bind("rdfs", RDFS)
    g.bind("owl", OWL)

    classes = [
        "Course",
        "Material",
        "Topic",
        "Subtopic",
        "Keyword"
    ]

    for cls in classes:
        g.add((MANARA[cls], RDF.type, OWL.Class))
        g.add((MANARA[cls], RDFS.label, Literal(cls)))

    object_properties = {
        "hasPrerequisite": ("Course", "Course"),
        "hasConcurrent": ("Course", "Course"),
        "hasMaterial": ("Course", "Material"),
        "hasTopic": ("Course", "Topic"),
        "coversTopic": ("Material", "Topic"),
        "hasSubtopic": ("Topic", "Subtopic"),
        "hasKeyword": ("Topic", "Keyword")
    }

    for prop, (domain_cls, range_cls) in object_properties.items():
        g.add((MANARA[prop], RDF.type, OWL.ObjectProperty))
        g.add((MANARA[prop], RDFS.domain, MANARA[domain_cls]))
        g.add((MANARA[prop], RDFS.range, MANARA[range_cls]))
        g.add((MANARA[prop], RDFS.label, Literal(prop)))

    datatype_properties = [
        "name",
        "courseCode",
        "chapter",
        "fileName",
        "relativePath",
        "fileType"
    ]

    for prop in datatype_properties:
        g.add((MANARA[prop], RDF.type, OWL.DatatypeProperty))
        g.add((MANARA[prop], RDFS.label, Literal(prop)))


# =========================================================
# GRAPH BUILDING
# =========================================================

def build_knowledge_graph(courses_dir: Path) -> Graph:
    g = Graph()
    add_schema(g)

    for course_dir in get_course_folders(courses_dir):
        course_name = course_dir.name
        metadata_dir = course_dir / "metadata"
        outputs_dir = course_dir / "outputs"

        course_uri = make_uri("course", course_name)

        g.add((course_uri, RDF.type, MANARA.Course))
        g.add((course_uri, MANARA.name, Literal(course_name)))
        g.add((course_uri, RDFS.label, Literal(course_name)))

        prereq_file = metadata_dir / "prerequisites.json"
        if prereq_file.exists():
            prereq_data = load_json_file(prereq_file)

            course_code = prereq_data.get("course_code", "")
            if course_code:
                g.add((course_uri, MANARA.courseCode, Literal(course_code)))

            for prereq in prereq_data.get("prerequisites", []):
                prereq_uri = make_uri("course", prereq)
                g.add((prereq_uri, RDF.type, MANARA.Course))
                g.add((prereq_uri, MANARA.name, Literal(prereq)))
                g.add((prereq_uri, RDFS.label, Literal(prereq)))
                g.add((course_uri, MANARA.hasPrerequisite, prereq_uri))

            for concurrent in prereq_data.get("concurrent", []):
                concurrent_uri = make_uri("course", concurrent)
                g.add((concurrent_uri, RDF.type, MANARA.Course))
                g.add((concurrent_uri, MANARA.name, Literal(concurrent)))
                g.add((concurrent_uri, RDFS.label, Literal(concurrent)))
                g.add((course_uri, MANARA.hasConcurrent, concurrent_uri))

        materials_map = {}

        materials_file = metadata_dir / "materials_index.json"
        if materials_file.exists():
            materials_data = load_json_file(materials_file)

            for material in materials_data.get("materials", []):
                material_id = material.get("material_id", safe_id(material.get("relative_path", "")))
                material_uri = make_uri("material", material_id)
                materials_map[material.get("relative_path", "")] = material_uri

                g.add((material_uri, RDF.type, MANARA.Material))
                g.add((material_uri, RDFS.label, Literal(material.get("file_name", material_id))))
                g.add((material_uri, MANARA.fileName, Literal(material.get("file_name", ""))))
                g.add((material_uri, MANARA.relativePath, Literal(material.get("relative_path", ""))))
                g.add((material_uri, MANARA.fileType, Literal(material.get("file_type", ""))))
                g.add((material_uri, MANARA.chapter, Literal(material.get("chapter", ""))))

                g.add((course_uri, MANARA.hasMaterial, material_uri))

        concepts_file = outputs_dir / "chapter_concepts.json"
        if concepts_file.exists():
            concepts_data = load_json_file(concepts_file)

            for relative_path, content in concepts_data.items():
                chapter = content.get("chapter", "")
                material_uri = materials_map.get(relative_path)

                for topic_index, topic in enumerate(content.get("topics", [])):
                    topic_name = topic.get("topic_name", "").strip()
                    if not topic_name:
                        continue

                    topic_uri = make_uri(
                        "topic",
                        f"{course_name}_{topic_name}_{topic_index}"
                    )

                    g.add((topic_uri, RDF.type, MANARA.Topic))
                    g.add((topic_uri, MANARA.name, Literal(topic_name)))
                    g.add((topic_uri, MANARA.chapter, Literal(chapter)))
                    g.add((topic_uri, RDFS.label, Literal(topic_name)))

                    g.add((course_uri, MANARA.hasTopic, topic_uri))

                    if material_uri is not None:
                        g.add((material_uri, MANARA.coversTopic, topic_uri))

                    for subtopic in topic.get("subtopics", []):
                        subtopic = subtopic.strip()
                        if not subtopic:
                            continue

                        subtopic_uri = make_uri(
                            "subtopic",
                            f"{course_name}_{subtopic}"
                        )

                        g.add((subtopic_uri, RDF.type, MANARA.Subtopic))
                        g.add((subtopic_uri, MANARA.name, Literal(subtopic)))
                        g.add((subtopic_uri, RDFS.label, Literal(subtopic)))

                        g.add((topic_uri, MANARA.hasSubtopic, subtopic_uri))

                    for keyword in topic.get("keywords", []):
                        keyword = keyword.strip()
                        if not keyword:
                            continue

                        keyword_uri = make_uri("keyword", keyword)

                        g.add((keyword_uri, RDF.type, MANARA.Keyword))
                        g.add((keyword_uri, MANARA.name, Literal(keyword)))
                        g.add((keyword_uri, RDFS.label, Literal(keyword)))

                        g.add((topic_uri, MANARA.hasKeyword, keyword_uri))

    return g


# =========================================================
# SAVE
# =========================================================

def main():
    g = build_knowledge_graph(COURSES_DIR)
    g.serialize(destination=str(OUTPUT_FILE), format="turtle")

    print("Semantic knowledge graph saved.")
    print("Output:", OUTPUT_FILE)
    print("Base URI:", BASE_URI)
    print("Total triples:", len(g))


if __name__ == "__main__":
    main()