package com.app.moneymate.buildlogic

import groovy.json.JsonOutput
import groovy.json.JsonSlurper
import org.gradle.api.Project
import org.gradle.api.artifacts.Configuration
import org.gradle.api.artifacts.component.ModuleComponentIdentifier
import org.gradle.api.artifacts.result.ResolvedDependencyResult
import org.gradle.api.artifacts.result.UnresolvedDependencyResult

object Inventory {
    fun write(module: Project) {
        val pins = DependencyPolicyPlugin.pins(module.rootProject.file("gradle/libs.versions.toml"))
        val scopes =
            module.configurations
                .filter { it.isCanBeResolved }
                .map { "module:${it.name}" to it } +
                module.buildscript.configurations
                    .filter { it.isCanBeResolved }
                    .map { "buildscript:${it.name}" to it }
        val graphs = scopes.map { (scope, configuration) -> graph(module, scope, configuration, pins) }
        val components = graphs.flatMap { it.first }.distinctBy { it["purl"] }.sortedBy { it["purl"].toString() }
        writeComponents(module, components)
        val graph =
            module.layout.buildDirectory
                .file("reports/security/dependency-graph.json")
                .get()
                .asFile
        graph.parentFile.mkdirs()
        graph.writeText(
            JsonOutput.toJson(
                mapOf(
                    "project" to module.path,
                    "graphs" to graphs.map { it.second },
                    "loadedClasses" to DependencyPolicyPlugin.loadedClasses(module, pins),
                ),
            ),
        )
    }

    private fun graph(
        module: Project,
        scope: String,
        configuration: Configuration,
        pins: Map<String, String>,
    ): Pair<List<Map<String, String>>, Map<String, Any>> {
        val result = configuration.incoming.resolutionResult
        check(result.allDependencies.none { it is UnresolvedDependencyResult }) {
            "Unresolved dependency in ${module.path}:$scope"
        }
        val modules = result.allComponents.filter { it.id is ModuleComponentIdentifier }.mapNotNull { it.moduleVersion }
        modules.forEach {
            pins["${it.group}:${it.name}"]?.let { expected ->
                check(it.version == expected) {
                    "Unexpected tooling version in ${module.path}:$scope: $it; expected $expected"
                }
            }
        }
        val components =
            modules.map {
                mapOf(
                    "type" to "library",
                    "group" to it.group,
                    "name" to it.name,
                    "version" to it.version,
                    "purl" to "pkg:maven/${it.group}/${it.name}@${it.version}",
                )
            }
        return components to
            mapOf(
                "scope" to scope,
                "components" to components,
                "selectionReasons" to
                    result.allComponents.map {
                        mapOf(
                            "id" to it.id.displayName,
                            "reasons" to it.selectionReason.descriptions.map { reason -> reason.description },
                        )
                    },
                "edges" to
                    result.allDependencies.filterIsInstance<ResolvedDependencyResult>().map {
                        mapOf(
                            "from" to it.from.id.displayName,
                            "requested" to it.requested.displayName,
                            "selected" to it.selected.id.displayName,
                        )
                    },
            )
    }

    fun combine(root: Project) {
        val components =
            root.allprojects
                .flatMap {
                    val file =
                        it.layout.buildDirectory
                            .file("reports/security/dependencies.cdx.json")
                            .get()
                            .asFile
                    val document = JsonSlurper().parse(file) as Map<*, *>
                    val entries = document["components"] as List<*>
                    entries.filterIsInstance<Map<*, *>>()
                }.distinctBy { it["purl"] }
                .sortedBy { it["purl"].toString() }
        writeComponents(root, components)
    }

    private fun writeComponents(
        module: Project,
        components: List<Any>,
    ) {
        val output =
            module.layout.buildDirectory
                .file("reports/security/dependencies.cdx.json")
                .get()
                .asFile
        output.parentFile.mkdirs()
        output.writeText(
            JsonOutput.toJson(
                mapOf("bomFormat" to "CycloneDX", "specVersion" to "1.5", "version" to 1, "components" to components),
            ),
        )
    }
}
