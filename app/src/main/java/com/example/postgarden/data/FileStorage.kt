package com.example.postgarden.data

import java.io.File

interface FileStorage {
    fun write(filename: String, content: String)
    fun read(filename: String): String?
    fun list(): List<String>
}

class AndroidFileStorage(private val rootDir: File) : FileStorage {
    override fun write(filename: String, content: String) {
        val file = File(rootDir, filename)
        file.writeText(content)
    }

    override fun read(filename: String): String? {
        val file = File(rootDir, filename)
        return if (file.exists()) file.readText() else null
    }

    override fun list(): List<String> {
        return rootDir.list()?.toList() ?: emptyList()
    }
}
